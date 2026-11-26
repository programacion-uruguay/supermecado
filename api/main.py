import re
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from scraper.db import get_connection, init_db
from scraper.run import scrape_once, DEFAULT_QUERIES


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

app = FastAPI(title="Precios Montevideo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "city": "Montevideo"}


@app.get("/api/supermarkets")
def list_supermarkets() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.slug, s.name, s.base_url, s.city,
                   COUNT(o.id) AS offer_count
            FROM supermarkets s
            LEFT JOIN offers o ON o.supermarket_id = s.id
            GROUP BY s.id
            ORDER BY s.name
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/categories")
def list_categories() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]
    finally:
        conn.close()


@app.get("/api/brands")
def list_brands() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT brand FROM products WHERE brand != '' ORDER BY brand"
        ).fetchall()
        return [r["brand"] for r in rows]
    finally:
        conn.close()


@app.get("/api/products")
def search_products(
    q: Optional[str] = Query(default="", description="Texto a buscar"),
    category: Optional[str] = Query(default="", description="Categoría"),
    brand: Optional[str] = Query(default="", description="Marca"),
    supermarket: Optional[str] = Query(default="", description="Slug de supermercado"),
    ingredient_key: Optional[str] = Query(default="", description="Clave de ingrediente de receta"),
    diet_tag: Optional[str] = Query(default="", description="Etiqueta dietética (ej: sin_tacc, sin_lactosa)"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    conn = get_connection()
    try:
        where_clauses = ["1=1"]
        params: list = []

        if q and q.strip():
            like = f"%{q.strip().lower()}%"
            where_clauses.append("(LOWER(p.display_name) LIKE ? OR LOWER(p.brand) LIKE ?)")
            params.extend([like, like])

        if category and category.strip():
            where_clauses.append("p.category = ?")
            params.append(category.strip())

        if brand and brand.strip():
            where_clauses.append("LOWER(p.brand) = ?")
            params.append(brand.strip().lower())

        if ingredient_key and ingredient_key.strip():
            where_clauses.append("p.ingredient_key = ?")
            params.append(ingredient_key.strip().lower())

        if diet_tag and diet_tag.strip():
            where_clauses.append("(',' || p.diet_tags || ',') LIKE ?")
            params.append(f"%,{diet_tag.strip().lower()},%")

        if supermarket and supermarket.strip():
            where_clauses.append(
                "EXISTS (SELECT 1 FROM offers o2 JOIN supermarkets s2 ON s2.id = o2.supermarket_id "
                "WHERE o2.product_id = p.id AND s2.slug = ?)"
            )
            params.append(supermarket.strip())

        where_sql = " AND ".join(where_clauses)
        products = conn.execute(
            f"""
            SELECT p.id, p.ean, p.display_name, p.brand, p.unit_size, p.category, p.ingredient_key, p.diet_tags
            FROM products p
            WHERE {where_sql}
            ORDER BY p.display_name
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()

        results = []
        for prod in products:
            offers = conn.execute(
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

            raw_offers = [dict(o) for o in offers]
            if not raw_offers:
                continue

            # Una oferta por supermercado (la más barata si hubo más de una)
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
            min_unit_price = offer_list[0].get("unit_price")
            unit_label = offer_list[0].get("unit_label", "")

            results.append(
                {
                    "id": prod["id"],
                    "ean": prod["ean"],
                    "name": prod["display_name"],
                    "brand": prod["brand"],
                    "unit_size": prod["unit_size"],
                    "category": prod["category"],
                    "ingredient_key": prod["ingredient_key"] or "",
                    "diet_tags": [t for t in (prod["diet_tags"] or "").split(",") if t],
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_unit_price": min_unit_price,
                    "unit_label": unit_label,
                    "savings": savings,
                    "savings_pct": savings_pct,
                    "cheapest_supermarket": offer_list[0]["supermarket_name"],
                    "offers": offer_list,
                }
            )

        results.sort(key=lambda x: (-len(x["offers"]), x["name"]))
        return results
    finally:
        conn.close()


@app.post("/api/scrape")
def trigger_scrape(
    background_tasks: BackgroundTasks,
    q: Optional[str] = Query(default=None, description="Término puntual a scrapear"),
) -> dict:
    queries = [q.strip()] if q and q.strip() else DEFAULT_QUERIES
    background_tasks.add_task(scrape_once, queries)
    return {"status": "started", "queries": queries}
