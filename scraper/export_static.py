import json
import re
from pathlib import Path
from typing import Optional
from scraper.db import get_connection, init_db, utc_now_iso


def compute_unit_price(price: float, unit_size: str) -> tuple[Optional[float], str]:
    """Calcula el precio por kg o por litro a partir de unit_size (ej: '500 g', '900 ml')."""
    if not unit_size or price <= 0:
        return None, ""
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*(kg|gr|g|ml|cc|lts|lt|l)\b", unit_size.lower())
    if not m:
        return None, ""
    qty = float(m.group(1).replace(",", "."))
    if qty <= 0:
        return None, ""
    unit = m.group(2)
    if unit in ("gr", "g"):
        return round(price / (qty / 1000.0), 2), "kg"
    if unit == "kg":
        return round(price / qty, 2), "kg"
    if unit in ("ml", "cc"):
        return round(price / (qty / 1000.0), 2), "L"
    if unit in ("l", "lt", "lts"):
        return round(price / qty, 2), "L"
    return None, ""

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "catalog.json"


def export_catalog(output_path: Path = DEFAULT_OUTPUT) -> int:
    """Exporta la base SQLite a un JSON estático para Firebase Hosting o GitHub Pages."""
    init_db()
    conn = get_connection()
    try:
        categories = [
            r["category"]
            for r in conn.execute(
                "SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category"
            ).fetchall()
        ]
        brands = [
            r["brand"]
            for r in conn.execute(
                "SELECT DISTINCT brand FROM products WHERE brand != '' ORDER BY brand"
            ).fetchall()
        ]
        supermarkets = [
            dict(r)
            for r in conn.execute(
                """
                SELECT s.id, s.slug, s.name, s.base_url, s.city, COUNT(o.id) AS offer_count
                FROM supermarkets s
                LEFT JOIN offers o ON o.supermarket_id = s.id
                GROUP BY s.id
                ORDER BY s.name
                """
            ).fetchall()
        ]

        products_rows = conn.execute(
            "SELECT id, ean, display_name, brand, unit_size, category, ingredient_key, diet_tags FROM products ORDER BY display_name"
        ).fetchall()

        products = []
        for prod in products_rows:
            raw_offers = [
                dict(o)
                for o in conn.execute(
                    """
                    SELECT o.id, o.title, o.price, o.list_price, o.currency, o.in_stock,
                           o.url, o.image_url, o.last_scraped_at,
                           s.slug AS supermarket_slug, s.name AS supermarket_name
                    FROM offers o
                    JOIN supermarkets s ON s.id = o.supermarket_id
                    WHERE o.product_id = ?
                    ORDER BY o.price ASC
                    """,
                    (prod["id"],),
                ).fetchall()
            ]
            if not raw_offers:
                continue

            seen_supers = set()
            offer_list = []
            for o in raw_offers:
                if o["supermarket_slug"] not in seen_supers:
                    seen_supers.add(o["supermarket_slug"])
                    u_price, u_label = compute_unit_price(o["price"], prod["unit_size"] or "")
                    o["unit_price"] = u_price
                    o["unit_label"] = u_label
                    offer_list.append(o)

            min_price = min(o["price"] for o in offer_list)
            max_price = max(o["price"] for o in offer_list)
            savings = round(max_price - min_price, 2)
            savings_pct = round((savings / max_price) * 100, 1) if max_price > 0 else 0.0
            diet_tags = [t for t in (prod["diet_tags"] or "").split(",") if t]

            products.append(
                {
                    "id": prod["id"],
                    "ean": prod["ean"],
                    "name": prod["display_name"],
                    "brand": prod["brand"],
                    "unit_size": prod["unit_size"],
                    "category": prod["category"],
                    "ingredient_key": prod["ingredient_key"] or "",
                    "diet_tags": diet_tags,
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_unit_price": offer_list[0].get("unit_price"),
                    "unit_label": offer_list[0].get("unit_label", ""),
                    "savings": savings,
                    "savings_pct": savings_pct,
                    "cheapest_supermarket": offer_list[0]["supermarket_name"],
                    "offers": offer_list,
                }
            )

        products.sort(key=lambda x: (-len(x["offers"]), x["name"]))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": utc_now_iso(),
            "categories": categories,
            "brands": brands,
            "supermarkets": supermarkets,
            "products": products,
        }
        raw_json = json.dumps(payload, ensure_ascii=False)
        output_path.write_text(raw_json, encoding="utf-8")

        # Sincronizar con web/dist si existe (para Firebase Hosting)
        dist_output = Path(__file__).resolve().parent.parent / "web" / "dist" / "data" / "catalog.json"
        if dist_output.parent.parent.exists():
            dist_output.parent.mkdir(parents=True, exist_ok=True)
            dist_output.write_text(raw_json, encoding="utf-8")

        # Sincronizar índice de ingredientes con el proyecto Cocina si está en el mismo entorno
        cocina_market_path = Path(__file__).resolve().parent.parent.parent / "Cocina" / "data" / "market-catalog.json"
        if cocina_market_path.parent.exists():
            by_ingredient: dict[str, list[dict]] = {}
            for prod in products:
                ikey = prod.get("ingredient_key") or ""
                if not ikey:
                    continue
                valid_offers = [
                    {
                        "supermarket_slug": o["supermarket_slug"],
                        "supermarket_name": o["supermarket_name"],
                        "price": round(float(o["price"])),
                        "url": o["url"],
                    }
                    for o in prod.get("offers", [])
                    if 15 <= float(o["price"]) <= 1800
                ]
                if not valid_offers:
                    continue
                by_ingredient.setdefault(ikey, []).append(
                    {
                        "id": prod["id"],
                        "ean": prod.get("ean") or "",
                        "name": prod["name"],
                        "brand": prod.get("brand") or "",
                        "unit_size": prod.get("unit_size") or "",
                        "category": prod.get("category") or "",
                        "ingredient_key": ikey,
                        "diet_tags": prod.get("diet_tags") or [],
                        "min_price": min(o["price"] for o in valid_offers),
                        "offers": {o["supermarket_slug"]: o for o in valid_offers},
                    }
                )
            for ikey, plist in by_ingredient.items():
                plist.sort(key=lambda x: (-len(x["offers"]), x["min_price"]))
                by_ingredient[ikey] = plist[:6]
            cocina_payload = {
                "generated_at": payload["generated_at"],
                "source": "precios.db (Precios Montevideo)",
                "total_ingredient_keys": len(by_ingredient),
                "by_ingredient": by_ingredient,
            }
            cocina_market_path.write_text(
                json.dumps(cocina_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        return len(products)
    finally:
        conn.close()


if __name__ == "__main__":
    count = export_catalog()
    print(f"Exportados {count} productos a {DEFAULT_OUTPUT}")
