import argparse
import asyncio
import logging
from .db import get_connection, init_db, upsert_offer, utc_now_iso
from .registry import get_adapters

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("precios-scraper")

RUBROS: dict[str, list[str]] = {
    "Almacén": [
        "yerba",
        "aceite",
        "arroz",
        "fideos",
        "azucar",
        "harina",
        "sal",
        "polenta",
        "lentejas",
        "porotos",
        "pulpa de tomate",
        "atun",
        "mayonesa",
        "vinagre",
        "caldo",
    ],
    "Desayuno y Dulces": [
        "cafe",
        "te",
        "galletas",
        "mermelada",
        "dulce de leche",
        "cacao",
    ],
    "Lácteos y Huevos": [
        "leche",
        "manteca",
        "yogur",
        "queso",
        "huevos",
        "ricota",
        "mozzarella",
        "queso rallado",
        "queso crema",
        "crema de leche",
    ],
    "Recetas, Pastas y Carnes": [
        "aceite de oliva",
        "avena",
        "maicena",
        "pan rallado",
        "tapas de empanadas",
        "lasana",
        "garbanzos",
        "arvejas",
        "choclo",
        "pechuga de pollo",
        "carne picada",
        "jamon cocido",
        "panceta",
        "chorizo",
        "merluza",
        "salmon",
    ],
    "Sin TACC y Dietas Especiales": [
        "premezcla sin gluten",
        "fideos sin gluten",
        "pan sin gluten",
        "galletas sin gluten",
        "leche deslactosada",
        "crema deslactosada",
        "bebida vegetal",
        "edulcorante stevia",
        "tofu",
        "soja texturizada",
        "fideos integrales",
        "arroz integral",
    ],
    "Bebidas": [
        "agua",
        "refresco",
        "jugo",
        "cerveza",
    ],
    "Limpieza": [
        "detergente",
        "jabon en polvo",
        "hipoclorito",
        "suavizante",
        "papel higienico",
        "rollo de cocina",
    ],
    "Perfumería": [
        "shampoo",
        "desodorante",
        "pasta dental",
        "jabon de tocador",
    ],
    "Congelados": [
        "hamburguesa",
        "papas fritas",
        "nuggets",
        "pizza congelada",
        "empanadas",
        "helado",
        "verduras congeladas",
        "milanesa",
    ],
    "Carnicería y Pollería": [
        "carne picada",
        "asado",
        "pollo",
        "chorizo",
        "pulpa",
    ],
    "Fiambrería y Embutidos": [
        "jamon",
        "paleta",
        "salame",
        "mortadela",
        "frankfurters",
        "muzzarella",
    ],
    "Frutas y Verduras": [
        "papa",
        "cebolla",
        "tomate",
        "zanahoria",
        "manzana",
        "banana",
    ],
    "Panadería": [
        "pan lactal",
        "pan flauta",
        "pan rallado",
        "bizcochos",
    ],
}

QUERY_TO_RUBRO: dict[str, str] = {
    q: rubro for rubro, q_list in RUBROS.items() for q in q_list
}

DEFAULT_QUERIES = [q for q_list in RUBROS.values() for q in q_list]

DEMO_DATA = [
    # (supermarket_slug, external_id, ean, title, brand, category, price, list_price, url)
    ("tienda_inglesa", "ti-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 259.0, 279.0, "https://www.tiendainglesa.com.uy"),
    ("disco", "di-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 249.0, None, "https://www.disco.com.uy"),
    ("devoto", "de-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 252.0, None, "https://www.devoto.com.uy"),
    ("geant", "ge-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 245.0, 265.0, "https://www.geant.com.uy"),
    ("tata", "ta-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 239.0, None, "https://www.tata.com.uy"),
    ("frog", "fr-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 255.0, None, "https://www.frog.com.uy"),
    ("el_dorado", "ed-101", "7730900100011", "Yerba Mate Canarias 1 kg", "Canarias", "Almacén", 244.0, None, "https://www.eldorado.com.uy"),

    ("tienda_inglesa", "ti-102", "7730123000012", "Leche Entera Conaprole 1 L", "Conaprole", "Lácteos", 49.0, None, "https://www.tiendainglesa.com.uy"),
    ("disco", "di-102", "7730123000012", "Leche Entera Conaprole 1 L", "Conaprole", "Lácteos", 48.0, None, "https://www.disco.com.uy"),
    ("devoto", "de-102", "7730123000012", "Leche Entera Conaprole 1 L", "Conaprole", "Lácteos", 48.0, None, "https://www.devoto.com.uy"),
    ("tata", "ta-102", "7730123000012", "Leche Entera Conaprole 1 L", "Conaprole", "Lácteos", 46.5, None, "https://www.tata.com.uy"),
    ("frog", "fr-102", "7730123000012", "Leche Entera Conaprole 1 L", "Conaprole", "Lácteos", 50.0, None, "https://www.frog.com.uy"),

    ("tienda_inglesa", "ti-103", "7730456000013", "Arroz Blanco Saman 1 kg", "Saman", "Almacén", 74.0, None, "https://www.tiendainglesa.com.uy"),
    ("disco", "di-103", "7730456000013", "Arroz Blanco Saman 1 kg", "Saman", "Almacén", 69.0, 76.0, "https://www.disco.com.uy"),
    ("geant", "ge-103", "7730456000013", "Arroz Blanco Saman 1 kg", "Saman", "Almacén", 68.0, None, "https://www.geant.com.uy"),
    ("tata", "ta-103", "7730456000013", "Arroz Blanco Saman 1 kg", "Saman", "Almacén", 71.0, None, "https://www.tata.com.uy"),
    ("el_dorado", "ed-103", "7730456000013", "Arroz Blanco Saman 1 kg", "Saman", "Almacén", 67.0, None, "https://www.eldorado.com.uy"),

    ("tienda_inglesa", "ti-104", "7730789000014", "Aceite de Girasol Óptimo 900 ml", "Óptimo", "Almacén", 118.0, None, "https://www.tiendainglesa.com.uy"),
    ("disco", "di-104", "7730789000014", "Aceite de Girasol Óptimo 900 ml", "Óptimo", "Almacén", 112.0, 125.0, "https://www.disco.com.uy"),
    ("devoto", "de-104", "7730789000014", "Aceite de Girasol Óptimo 900 ml", "Óptimo", "Almacén", 114.0, None, "https://www.devoto.com.uy"),
    ("tata", "ta-104", "7730789000014", "Aceite de Girasol Óptimo 900 ml", "Óptimo", "Almacén", 109.0, None, "https://www.tata.com.uy"),
    ("frog", "fr-104", "7730789000014", "Aceite de Girasol Óptimo 900 ml", "Óptimo", "Almacén", 119.0, None, "https://www.frog.com.uy"),

    ("disco", "di-105", "7730321000015", "Fideos Tallarines Adria 500 g", "Adria", "Pastas", 59.0, None, "https://www.disco.com.uy"),
    ("geant", "ge-105", "7730321000015", "Fideos Tallarines Adria 500 g", "Adria", "Pastas", 56.0, None, "https://www.geant.com.uy"),
    ("tata", "ta-105", "7730321000015", "Fideos Tallarines Adria 500 g", "Adria", "Pastas", 54.0, 62.0, "https://www.tata.com.uy"),
    ("el_dorado", "ed-105", "7730321000015", "Fideos Tallarines Adria 500 g", "Adria", "Pastas", 57.0, None, "https://www.eldorado.com.uy"),
]


def seed_demo_data() -> int:
    init_db()
    conn = get_connection()
    try:
        for item in DEMO_DATA:
            slug, ext_id, ean, title, brand, category, price, list_price, url = item
            upsert_offer(
                conn,
                slug,
                ext_id,
                title,
                price,
                url,
                ean=ean,
                brand=brand,
                category=category,
                list_price=list_price,
            )
        conn.commit()
        logger.info("Cargados %d precios de ejemplo en la base de datos.", len(DEMO_DATA))
        return len(DEMO_DATA)
    finally:
        conn.close()

    try:
        from .export_static import export_catalog

        exported = export_catalog()
        logger.info("Catálogo estático actualizado (%d productos).", exported)
    except Exception as exc:
        logger.warning("No se pudo exportar catalog.json: %s", exc)


async def scrape_once(queries: list[str], supermarkets: list[str] | None = None, limit: int = 15) -> None:
    init_db()
    adapters = get_adapters()
    selected = (
        {k: v for k, v in adapters.items() if k in supermarkets}
        if supermarkets
        else adapters
    )

    conn = get_connection()
    try:
        for slug, adapter in selected.items():
            started_at = utc_now_iso()
            total_items = 0
            error_msg = ""
            status = "ok"

            for q in queries:
                try:
                    logger.info("[%s] Buscando '%s'...", slug, q)
                    items = await adapter.search(q, limit=limit)
                    for p in items:
                        category = p.category
                        if not category or category == "General":
                            category = QUERY_TO_RUBRO.get(q, "General")
                        upsert_offer(
                            conn,
                            slug,
                            p.external_id,
                            p.title,
                            p.price,
                            p.url,
                            ean=p.ean,
                            brand=p.brand,
                            category=category,
                            list_price=p.list_price,
                            in_stock=p.in_stock,
                            image_url=p.image_url,
                        )
                    total_items += len(items)
                except Exception as exc:
                    status = "partial_error"
                    error_msg += f"{q}: {exc}; "
                    logger.warning("[%s] Error buscando '%s': %s", slug, q, exc)

            conn.execute(
                """
                INSERT INTO scrape_runs (supermarket_slug, status, items_found, error_message, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (slug, status, total_items, error_msg[:500], started_at, utc_now_iso()),
            )
            conn.commit()
            logger.info("[%s] Finalizado (%s): %d productos guardados.", slug, status, total_items)
    finally:
        conn.close()

    try:
        from .export_static import export_catalog

        exported = export_catalog()
        logger.info("Catálogo estático actualizado (%d productos).", exported)
    except Exception as exc:
        logger.warning("No se pudo exportar catalog.json: %s", exc)


def run_scheduler(queries: list[str], supermarkets: list[str] | None, interval_hours: int) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler()

    def job():
        asyncio.run(scrape_once(queries, supermarkets))

    logger.info("Iniciando autoalimentación cada %d horas...", interval_hours)
    job()  # Primera ejecución inmediata
    scheduler.add_job(job, "interval", hours=interval_hours)
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de precios de supermercados de Montevideo")
    parser.add_argument("--demo", action="store_true", help="Carga datos de ejemplo para probar la web")
    parser.add_argument("--queries", nargs="+", default=None, help="Términos de búsqueda")
    parser.add_argument("--rubro", default=None, help="Rubro específico (ej. Limpieza, Bebidas)")
    parser.add_argument("--supermarkets", nargs="+", default=None, help="Slugs de supermercados a consultar")
    parser.add_argument("--schedule", type=int, default=0, help="Ejecutar automáticamente cada N horas")
    args = parser.parse_args()

    if args.demo:
        seed_demo_data()
        return

    if args.queries:
        queries = args.queries
    elif args.rubro:
        matched = [v for k, v in RUBROS.items() if k.lower() == args.rubro.strip().lower()]
        if not matched:
            raise SystemExit(f"Rubro desconocido '{args.rubro}'. Opciones: {', '.join(RUBROS.keys())}")
        queries = matched[0]
    else:
        queries = DEFAULT_QUERIES

    if args.schedule > 0:
        run_scheduler(queries, args.supermarkets, args.schedule)
    else:
        asyncio.run(scrape_once(queries, args.supermarkets))


if __name__ == "__main__":
    main()
