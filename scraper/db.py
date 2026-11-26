import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "precios.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS supermarkets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                city TEXT NOT NULL DEFAULT 'Montevideo'
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ean TEXT UNIQUE,
                normalized_name TEXT NOT NULL,
                canonical_key TEXT DEFAULT '',
                display_name TEXT NOT NULL,
                brand TEXT DEFAULT '',
                unit_size TEXT DEFAULT '',
                category TEXT DEFAULT 'General'
            );

            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supermarket_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                list_price REAL,
                currency TEXT NOT NULL DEFAULT 'UYU',
                in_stock INTEGER NOT NULL DEFAULT 1,
                url TEXT NOT NULL,
                image_url TEXT DEFAULT '',
                last_scraped_at TEXT NOT NULL,
                UNIQUE(supermarket_id, external_id),
                FOREIGN KEY (supermarket_id) REFERENCES supermarkets(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                price REAL NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supermarket_slug TEXT NOT NULL,
                status TEXT NOT NULL,
                items_found INTEGER NOT NULL DEFAULT 0,
                error_message TEXT DEFAULT '',
                started_at TEXT NOT NULL,
                finished_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_products_norm ON products(normalized_name);
            CREATE INDEX IF NOT EXISTS idx_offers_price ON offers(price);
            CREATE INDEX IF NOT EXISTS idx_offers_product ON offers(product_id);
            """
        )

        supermarkets = [
            ("tienda_inglesa", "Tienda Inglesa", "https://www.tiendainglesa.com.uy", "Montevideo"),
            ("disco", "Disco", "https://www.disco.com.uy", "Montevideo"),
            ("devoto", "Devoto", "https://www.devoto.com.uy", "Montevideo"),
            ("geant", "Géant", "https://www.geant.com.uy", "Montevideo"),
            ("tata", "Tata", "https://www.tata.com.uy", "Montevideo"),
            ("frog", "Frog", "https://frog.uy", "Montevideo"),
            ("el_dorado", "El Dorado", "https://www.eldorado.com.uy", "Montevideo"),
            ("el_clon", "El Clon", "https://www.elclon.com.uy", "Montevideo"),
            ("redmarket5", "RedMarket5", "https://redmarket5.com.uy", "Montevideo"),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO supermarkets (slug, name, base_url, city)
            VALUES (?, ?, ?, ?)
            """,
            supermarkets,
        )

        # Migración segura si la tabla products ya existía sin unit_size, canonical_key, ingredient_key o diet_tags
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(products)").fetchall()]
        if "unit_size" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN unit_size TEXT DEFAULT ''")
        if "canonical_key" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN canonical_key TEXT DEFAULT ''")
        if "ingredient_key" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN ingredient_key TEXT DEFAULT ''")
        if "diet_tags" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN diet_tags TEXT DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_canonical ON products(canonical_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_ingredient ON products(ingredient_key)")

        conn.commit()
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(text: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


KNOWN_BRANDS = [
    "Tienda Inglesa",
    "La Selva",
    "Del Cebador",
    "Blue Patna",
    "Green Chef",
    "Las Acacias",
    "Río de la Plata",
    "El Chaná",
    "Santa Teresa",
    "Canarias",
    "Baldo",
    "Sara",
    "Armiño",
    "Contigo",
    "Cabral",
    "Conaprole",
    "Parmalat",
    "Claldy",
    "Calcar",
    "Saman",
    "Óptimo",
    "Optimo",
    "Uruguay",
    "Adria",
    "Puritas",
    "Cañuelas",
    "Arcor",
    "Hellmann's",
    "Hellmanns",
    "Heinz",
    "Nescafé",
    "Bracafé",
    "Salus",
    "Nativa",
    "Matutina",
    "Tata",
    "Ta-Ta",
    "Disco",
    "Cololo",
    "Knorr",
    "Maggi",
    "Sadia",
    "Bimbo",
    "Pagnifique",
    "Lays",
    "Coca-Cola",
    "Pepsi",
    "Nix",
    "Fagar",
]


def infer_brand_and_size(title: str, explicit_brand: str = "") -> tuple[str, str]:
    """Separa la marca y la presentación/peso (ej. '1 kg', '900 ml') del título del producto."""
    import re

    clean_title = title.strip()

    # 1. Extraer peso/volumen (ej: 1 kg, 500 g, 900 ml, 1.5 L, 6.25 L, 1 un.)
    size_match = re.search(
        r"\b(\d+(?:[.,]\d+)?\s*(?:kg|gr|g|ml|cc|l|lt|lts|un\.?|unidades))\b",
        clean_title,
        flags=re.IGNORECASE,
    )
    unit_size = size_match.group(1).strip() if size_match else ""

    # 2. Marca explícita si viene del supermercado
    brand = explicit_brand.strip()
    if brand:
        brand = " ".join(w.capitalize() if w.isupper() else w for w in brand.split())
        return brand, unit_size

    # 3. Buscar marcas conocidas en el título
    lower_title = clean_title.lower()
    for known in KNOWN_BRANDS:
        if re.search(rf"\b{re.escape(known.lower())}\b", lower_title):
            return known, unit_size

    # 4. Detectar palabras consecutivas en MAYÚSCULAS (ej: TIENDA INGLESA, SALUS, CONTIGO)
    caps_match = re.search(r"\b([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)\b", clean_title)
    if caps_match:
        candidate = caps_match.group(1).strip()
        if candidate not in {"SIN", "CON", "PARA", "TIPO", "PACK", "UYU"}:
            return candidate.title(), unit_size

    return "", unit_size


STOPWORDS_ES = {
    "de", "del", "la", "el", "los", "las", "y", "e", "en", "para", "por",
    "tipo", "bolsa", "paquete", "botella", "envase", "sachet", "doypack",
    "caja", "lata", "frasco", "unidad", "un", "mate",
}


def normalize_unit_token(size: str) -> str:
    """Normaliza unidades: '1000 g' -> '1kg', '1 L' -> '1l', '500 gr' -> '500g'."""
    import re

    if not size:
        return ""
    s = size.lower().replace(",", ".").strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(kg|gr|g|ml|cc|lts|lt|l|un\.?|unidades)$", s)
    if not m:
        return re.sub(r"\s+", "", s)
    val = float(m.group(1))
    unit = m.group(2)
    if unit in ("gr", "g"):
        if val >= 1000 and val % 1000 == 0:
            return f"{int(val // 1000)}kg"
        return f"{int(val) if val.is_integer() else val}g"
    if unit in ("kg",):
        return f"{int(val) if val.is_integer() else val}kg"
    if unit in ("ml", "cc"):
        if val >= 1000 and val % 1000 == 0:
            return f"{int(val // 1000)}l"
        return f"{int(val) if val.is_integer() else val}ml"
    if unit in ("l", "lt", "lts"):
        return f"{int(val) if val.is_integer() else val}l"
    return f"{int(val) if val.is_integer() else val}un"


def build_canonical_key(title: str, brand: str = "", unit_size: str = "") -> str:
    """Genera una huella canónica para unificar el mismo producto entre supermercados."""
    import re

    norm = normalize_text(title)
    # Unir número+unidad para que '1 kg' y '1kg' sean el mismo token
    norm = re.sub(
        r"\b(\d+(?:\.\d+)?)\s+(kg|gr|g|ml|cc|lts|lt|l|un)\b",
        lambda m: normalize_unit_token(f"{m.group(1)} {m.group(2)}"),
        norm,
    )
    tokens = []
    for tok in norm.split():
        if tok in STOPWORDS_ES:
            continue
        # Normalizar plurales simples en español (fideos -> fideo, tallarines -> tallarin)
        if tok == "fideos":
            tok = "fideo"
        elif tok == "tallarines":
            tok = "tallarin"
        tokens.append(tok)

    if brand:
        for bt in normalize_text(brand).split():
            if bt not in STOPWORDS_ES and bt not in tokens:
                tokens.append(bt)

    norm_size = normalize_unit_token(unit_size)
    if norm_size and norm_size not in tokens:
        tokens.append(norm_size)

    unique_sorted = sorted(set(tokens))
    return "|".join(unique_sorted)


def infer_ingredient_and_diet_tags(title: str, category: str = "") -> tuple[str, str]:
    """
    Clasifica un producto de supermercado en su clave de ingrediente culinario (`ingredient_key`)
    y sus etiquetas dietéticas (`diet_tags`: sin_tacc, sin_lactosa, sin_azucar, integral, descremado, vegano).
    """
    import re

    t = normalize_text(f"{title} {category}")
    # Excluir productos de limpieza, higiene o mascotas para no asociarlos a recetas
    if re.search(
        r"\b(detergente|hipoclorito|jabon|shampoo|acondicionador|desodorante|talco|papel higienico|rollo de cocina|suavizante|limpiador|esponja|cepillo|pasta dental|pañal|perro|gato|mascota|juguete|pileta|gorra)\b",
        t,
    ):
        return "", ""

    tags: list[str] = []
    is_gf = bool(re.search(r"\b(sin tacc|sin gluten|gluten free|libre de gluten|celiac)\b", t))
    is_lf = bool(re.search(r"\b(sin lactosa|deslactosad\w*|0 lactosa|libre de lactosa)\b", t))
    is_sf = bool(re.search(r"\b(sin azucar|0 azucar|zero|stevia|edulcorante|sucralosa|light|diet)\b", t))
    is_int = bool(re.search(r"\b(integral\w*|salvado)\b", t))
    is_lowfat = bool(re.search(r"\b(descremad\w*|magr\w*|light|0 grasa)\b", t))
    is_veg = bool(re.search(r"\b(vegan\w*|vegetal|tofu|soja texturizada)\b", t))

    if is_gf:
        tags.append("sin_tacc")
    if is_lf:
        tags.append("sin_lactosa")
    if is_sf:
        tags.append("sin_azucar")
    if is_int:
        tags.append("integral")
    if is_lowfat:
        tags.append("descremado")
    if is_veg:
        tags.append("vegano")

    ing_key = ""
    # 1. Productos específicos Sin TACC / Sin Gluten
    if is_gf:
        if re.search(r"\b(premezcla|harina)\b", t):
            ing_key = "harina_sin_tacc"
        elif re.search(r"\b(fideo|tallarin|spaghetti|espagueti|tirabuzon|penne|mostachol|macarron|codito|moñito|pasta)\b", t):
            ing_key = "fideos_sin_tacc"
        elif re.search(r"\b(lasana|lasaña)\b", t):
            ing_key = "lasana_sin_tacc"
        elif re.search(r"\b(pan rallado|rebozador)\b", t):
            ing_key = "rebozador_sin_tacc"
        elif re.search(r"\b(tapa|empanada|pascualina)\b", t):
            ing_key = "tapas_sin_tacc"
        elif re.search(r"\b(pan|molde|lactal|baguette)\b", t):
            ing_key = "pan_sin_tacc"
        elif re.search(r"\b(avena)\b", t):
            ing_key = "avena_sin_tacc"
        elif re.search(r"\b(polenta)\b", t):
            ing_key = "polenta_sin_tacc"
        elif re.search(r"\b(galleta|galletita)\b", t):
            ing_key = "galletas_sin_tacc"

    # 2. Fécula / Maicena (naturalmente sin TACC)
    if not ing_key and re.search(r"\b(maicena|maizena|fecula de maiz|almidon de maiz|fecula de mandioca)\b", t):
        ing_key = "maicena"
        if "sin_tacc" not in tags:
            tags.append("sin_tacc")

    # 3. Lácteos y alternativas Sin Lactosa / Vegetales
    if not ing_key:
        if re.search(r"\b(bebida vegetal|leche de almendra|leche de avena|leche de soja)\b", t):
            ing_key = "bebida_vegetal"
            for tg in ("sin_lactosa", "vegano"):
                if tg not in tags:
                    tags.append(tg)
        elif re.search(r"\b(crema vegetal)\b", t):
            ing_key = "crema_vegetal"
            for tg in ("sin_lactosa", "vegano"):
                if tg not in tags:
                    tags.append(tg)
        elif re.search(r"\b(queso vegetal|mozzarella vegetal|levadura nutricional)\b", t):
            ing_key = "queso_vegetal"
            for tg in ("sin_lactosa", "vegano"):
                if tg not in tags:
                    tags.append(tg)
        elif re.search(r"\b(tofu)\b", t):
            ing_key = "tofu"
            for tg in ("sin_lactosa", "vegano", "sin_tacc"):
                if tg not in tags:
                    tags.append(tg)
        elif re.search(r"\b(soja texturizada|proteina de soja)\b", t):
            ing_key = "soja_texturizada"
            for tg in ("sin_lactosa", "vegano"):
                if tg not in tags:
                    tags.append(tg)
        elif re.search(r"\b(crema de leche|crema doble)\b", t) and not re.search(r"\bdulce\b", t):
            ing_key = "crema_deslactosada" if is_lf else "crema_de_leche"
        elif re.search(r"\b(dulce de leche|dulce crema de leche)\b", t):
            ing_key = "dulce_de_leche"
        elif re.search(r"\b(leche)\b", t) and not re.search(r"\b(chocolatada|colet|condensada|polvo)\b", t):
            ing_key = "leche_deslactosada" if is_lf else ("leche_descremada" if is_lowfat else "leche")
        elif re.search(r"\b(manteca)\b", t):
            ing_key = "manteca"
        elif re.search(r"\b(margarina)\b", t):
            ing_key = "margarina"
        elif re.search(r"\b(yogur|yogurt)\b", t):
            ing_key = "yogur"
        elif re.search(r"\b(ricota|ricotta)\b", t):
            ing_key = "ricota"
        elif re.search(r"\b(mozzarella|muzzarella)\b", t):
            ing_key = "queso_sin_lactosa" if is_lf else "mozzarella"
        elif re.search(r"\b(queso rallado|parmesano|sardo|provolone)\b", t):
            ing_key = "queso_rallado"
        elif re.search(r"\b(queso crema|queso untable|requeson|mascarpone)\b", t):
            ing_key = "queso_sin_lactosa" if is_lf else "queso_crema"
        elif re.search(r"\b(queso azul|roquefort)\b", t):
            ing_key = "queso_azul"
        elif re.search(r"\b(queso|colonia|dambo|gruyere|cheddar|port salut|feta|brie)\b", t):
            ing_key = "queso_sin_lactosa" if is_lf else "queso_colonia"
        elif re.search(r"\b(huevo|huevos)\b", t) and not re.search(
            r"\b(pascua|fideo|tallarin|spaghetti|cinta|pasta|lasana|noqui|raviol|mayonesa|galleta|bizcochuelo)\b",
            t,
        ):
            ing_key = "huevos"

    # 4. Pastas, Harinas, Arroz, Panificados y Legumbres
    if not ing_key:
        if re.search(r"\b(lasana|lasaña)\b", t):
            ing_key = "laminas_lasana"
        elif re.search(r"\b(panqueque|canelon)\b", t):
            ing_key = "panqueques"
        elif re.search(r"\b(tapa|empanada|copetin|pascualina)\b", t):
            ing_key = "tapas_empanadas"
        elif re.search(r"\b(noqui|ñoqui|raviol|sorrentino|capelet)\b", t):
            ing_key = "pasta_fresca"
        elif re.search(r"\b(fideo|tallarin|spaghetti|espagueti|fettuccini|tirabuzon|penne|mostachol|macarron|rigatoni|caracol|moñito|codito|dedalito|nido)\b", t):
            ing_key = "fideos_integrales" if is_int else "fideos"
        elif re.search(r"\b(arroz)\b", t) and not re.search(r"\bgalleta|harina\b", t):
            ing_key = "arroz_integral" if is_int else "arroz"
        elif re.search(r"\b(semola)\b", t):
            ing_key = "semola"
        elif re.search(r"\b(trigo burgol|burgol)\b", t):
            ing_key = "trigo_burgol"
        elif re.search(r"\b(polenta|harina de maiz)\b", t):
            ing_key = "polenta"
            if "sin_tacc" not in tags:
                tags.append("sin_tacc")
        elif re.search(r"\b(avena)\b", t):
            ing_key = "avena"
        elif re.search(r"\b(harina)\b", t):
            ing_key = "harina_integral" if is_int else "harina_trigo"
        elif re.search(r"\b(pan rallado|rebozador)\b", t):
            ing_key = "pan_rallado"
        elif re.search(r"\b(pan|miñon|baguette|lactal|arabe|pita|tortilla)\b", t):
            ing_key = "pan_integral" if is_int else "pan_molde"
        elif re.search(r"\b(galleta de arroz)\b", t):
            ing_key = "galletas_sin_tacc"
            if "sin_tacc" not in tags:
                tags.append("sin_tacc")
        elif re.search(r"\b(galleta|galletita)\b", t):
            ing_key = "galletas"
        elif re.search(r"\b(levadura|polvo de hornear)\b", t):
            ing_key = "levadura"
        elif re.search(r"\b(lenteja)\b", t):
            ing_key = "lentejas"
        elif re.search(r"\b(poroto)\b", t):
            ing_key = "porotos"
        elif re.search(r"\b(garbanzo)\b", t):
            ing_key = "garbanzos"
        elif re.search(r"\b(arveja)\b", t):
            ing_key = "arvejas"
        elif re.search(r"\b(choclo)\b", t):
            ing_key = "choclo"

    # 5. Carnes, Pollo, Fiambres y Pescados
    if not ing_key:
        if re.search(r"\b(pechuga|suprema|muslo|pollo)\b", t) and not re.search(r"\bcaldo\b", t):
            ing_key = "pechuga_pollo"
        elif re.search(r"\b(carne picada|picada magra|picada especial)\b", t):
            ing_key = "carne_picada"
        elif re.search(r"\b(bife|colita|cuadril|nalga|peceto|lomo|asado|carne vacuna)\b", t) and not re.search(r"\bcaldo\b", t):
            ing_key = "carne_vacuna"
        elif re.search(r"\b(cerdo|bondiola|costilla|solomillo)\b", t):
            ing_key = "cerdo"
        elif re.search(r"\b(chorizo)\b", t):
            ing_key = "chorizo"
        elif re.search(r"\b(panceta|bacon)\b", t):
            ing_key = "panceta"
        elif re.search(r"\b(jamon crudo)\b", t):
            ing_key = "jamon_crudo"
        elif re.search(r"\b(jamon|lomito)\b", t):
            ing_key = "jamon_cocido"
        elif re.search(r"\b(salmon)\b", t):
            ing_key = "salmon"
        elif re.search(r"\b(merluza|corvina|brotola|pescado)\b", t) and not re.search(r"\bcaldo\b", t):
            ing_key = "merluza"
        elif re.search(r"\b(atun)\b", t):
            ing_key = "atun"
        elif re.search(r"\b(camaron|marisco|mejillon)\b", t):
            ing_key = "camarones"
        elif re.search(r"\b(anchoa)\b", t):
            ing_key = "anchoas"

    # 6. Aceites, Salsas, Condimentos, Endulzantes y Frutos Secos
    if not ing_key:
        if re.search(r"\b(aceite de oliva|oliva)\b", t) and re.search(r"\baceite\b", t):
            ing_key = "aceite_oliva"
        elif re.search(r"\b(aceite)\b", t):
            ing_key = "aceite_girasol"
        elif re.search(r"\b(aceto)\b", t):
            ing_key = "aceto"
        elif re.search(r"\b(vinagre)\b", t):
            ing_key = "vinagre"
        elif re.search(r"\b(mayonesa)\b", t):
            ing_key = "mayonesa"
        elif re.search(r"\b(mostaza)\b", t):
            ing_key = "mostaza"
        elif re.search(r"\b(extracto.*tomate)\b", t):
            ing_key = "extracto_tomate"
        elif re.search(r"\b(pulpa de tomate|pure de tomate|salsa de tomate|tomate triturado|tomate perita en lata)\b", t):
            ing_key = "pulpa_tomate_sin_azucar" if is_sf else "pulpa_tomate"
        elif re.search(r"\b(caldo)\b", t):
            ing_key = "caldo"
        elif re.search(r"\b(mermelada)\b", t):
            ing_key = "mermelada_sin_azucar" if is_sf else "mermelada"
        elif re.search(r"\b(membrillo)\b", t):
            ing_key = "membrillo"
        elif re.search(r"\b(coco rallado|coco)\b", t):
            ing_key = "coco_rallado"
        elif re.search(r"\b(vino)\b", t):
            ing_key = "vino"
        elif re.search(r"\b(edulcorante|stevia|sucralosa|eritritol)\b", t):
            ing_key = "edulcorante"
            if "sin_azucar" not in tags:
                tags.append("sin_azucar")
        elif re.search(r"\b(azucar)\b", t) and not re.search(r"\b(sin azucar|0 azucar|refresco|jugo|galleta|mermelada|pulpa|dulce)\b", t):
            ing_key = "azucar"
        elif re.search(r"\b(miel)\b", t):
            ing_key = "miel"
        elif re.search(r"\b(cacao|chocolate)\b", t):
            ing_key = "cacao"
        elif re.search(r"\b(nuez|nueces|almendra|avellana|castaña)\b", t):
            ing_key = "frutos_secos"
        elif re.search(r"\b(mani|pasta de mani)\b", t):
            ing_key = "mani"
        elif re.search(r"\b(semilla|sesamo|chia|lino|girasol)\b", t) and not re.search(r"\baceite\b", t):
            ing_key = "semillas"
        elif re.search(r"\b(aceituna)\b", t):
            ing_key = "aceitunas"
        elif re.search(r"\b(alcaparra)\b", t):
            ing_key = "alcaparras"
        elif re.search(r"\b(sal)\b", t):
            ing_key = "sal"
        elif re.search(r"\b(oregano|pimenton|pimienta|comino|nuez moscada|canela|laurel|romero|tomillo|albahaca|perejil|eneldo)\b", t):
            ing_key = "especias"

    # 7. Verdulería y Frutería
    if not ing_key:
        if re.search(r"\b(papa)\b", t):
            ing_key = "papa"
        elif re.search(r"\b(boniato)\b", t):
            ing_key = "boniato"
        elif re.search(r"\b(calabaza|zapallo|cabutia)\b", t):
            ing_key = "calabaza"
        elif re.search(r"\b(cebolla de verdeo|verdeo|puerro)\b", t):
            ing_key = "cebolla_verdeo"
        elif re.search(r"\b(cebolla)\b", t):
            ing_key = "cebolla"
        elif re.search(r"\b(ajo)\b", t):
            ing_key = "ajo"
        elif re.search(r"\b(tomate seco)\b", t):
            ing_key = "tomates_secos"
        elif re.search(r"\b(tomate|cherry)\b", t):
            ing_key = "tomate"
        elif re.search(r"\b(morron|aji)\b", t):
            ing_key = "morron"
        elif re.search(r"\b(zanahoria)\b", t):
            ing_key = "zanahoria"
        elif re.search(r"\b(espinaca)\b", t):
            ing_key = "espinaca"
        elif re.search(r"\b(acelga)\b", t):
            ing_key = "acelga"
        elif re.search(r"\b(brocoli|coliflor)\b", t):
            ing_key = "brocoli"
        elif re.search(r"\b(berenjena)\b", t):
            ing_key = "berenjena"
        elif re.search(r"\b(zapallito|zucchini)\b", t):
            ing_key = "zapallito"
        elif re.search(r"\b(champinon|portobello|hongo)\b", t):
            ing_key = "champinones"
        elif re.search(r"\b(esparrago)\b", t):
            ing_key = "esparragos"
        elif re.search(r"\b(palta)\b", t):
            ing_key = "palta"
        elif re.search(r"\b(lechuga|rucula|repollo|pepino|apio)\b", t):
            ing_key = "verduras_hoja"
        elif re.search(r"\b(limon|naranja|pomelo|manzana|banana|frutilla|frambuesa|durazno|ciruela|pera|anana|sandia|kiwi|uva)\b", t):
            ing_key = "frutas"

    return ing_key, ",".join(tags)


def backfill_products_metadata(db_path: Path = DB_PATH) -> int:
    """Completa marca, presentación, clave canónica y fusiona duplicados entre supermercados."""
    init_db(db_path)
    conn = get_connection(db_path)
    updated = 0
    try:
        rows = conn.execute(
            "SELECT id, ean, display_name, brand, unit_size, category, canonical_key, ingredient_key, diet_tags FROM products"
        ).fetchall()
        for r in rows:
            inferred_brand, inferred_size = infer_brand_and_size(r["display_name"], r["brand"] or "")
            new_brand = inferred_brand or (r["brand"] or "")
            if new_brand and new_brand.isupper():
                new_brand = new_brand.title()
            new_size = r["unit_size"] or inferred_size
            new_key = build_canonical_key(r["display_name"], new_brand, new_size)
            ing_key, d_tags = infer_ingredient_and_diet_tags(r["display_name"], r["category"] or "")
            new_ing = ing_key or (r["ingredient_key"] or "")
            new_tags = d_tags or (r["diet_tags"] or "")
            if (
                new_brand != (r["brand"] or "")
                or new_size != (r["unit_size"] or "")
                or new_key != (r["canonical_key"] or "")
                or new_ing != (r["ingredient_key"] or "")
                or new_tags != (r["diet_tags"] or "")
            ):
                conn.execute(
                    "UPDATE products SET brand = ?, unit_size = ?, canonical_key = ?, ingredient_key = ?, diet_tags = ? WHERE id = ?",
                    (new_brand, new_size, new_key, new_ing, new_tags, r["id"]),
                )
                updated += 1

        # Fusionar productos duplicados que comparten canonical_key
        groups = conn.execute(
            """
            SELECT canonical_key, COUNT(*) AS cnt
            FROM products
            WHERE canonical_key != ''
            GROUP BY canonical_key
            HAVING cnt > 1
            """
        ).fetchall()

        merged = 0
        for g in groups:
            prods = conn.execute(
                """
                SELECT p.id, p.ean, p.display_name,
                       (SELECT COUNT(*) FROM offers o WHERE o.product_id = p.id) AS offer_cnt
                FROM products p
                WHERE p.canonical_key = ?
                ORDER BY (p.ean IS NOT NULL) DESC, offer_cnt DESC, p.id ASC
                """,
                (g["canonical_key"],),
            ).fetchall()
            keeper_id = prods[0]["id"]
            for dup in prods[1:]:
                dup_id = dup["id"]
                dup_offers = conn.execute(
                    "SELECT id, supermarket_id, external_id FROM offers WHERE product_id = ?",
                    (dup_id,),
                ).fetchall()
                for off in dup_offers:
                    conflict = conn.execute(
                        "SELECT id FROM offers WHERE supermarket_id = ? AND external_id = ? AND product_id = ?",
                        (off["supermarket_id"], off["external_id"], keeper_id),
                    ).fetchone()
                    if not conflict:
                        conn.execute(
                            "UPDATE offers SET product_id = ? WHERE id = ?",
                            (keeper_id, off["id"]),
                        )
                conn.execute("DELETE FROM offers WHERE product_id = ?", (dup_id,))
                conn.execute("DELETE FROM products WHERE id = ?", (dup_id,))
                merged += 1

        conn.commit()
        return updated + merged
    finally:
        conn.close()


def upsert_offer(
    conn: sqlite3.Connection,
    supermarket_slug: str,
    external_id: str,
    title: str,
    price: float,
    url: str,
    *,
    ean: Optional[str] = None,
    brand: str = "",
    category: str = "General",
    list_price: Optional[float] = None,
    in_stock: bool = True,
    image_url: str = "",
) -> None:
    row = conn.execute(
        "SELECT id FROM supermarkets WHERE slug = ?", (supermarket_slug,)
    ).fetchone()
    if not row:
        raise ValueError(f"Supermercado desconocido: {supermarket_slug}")
    supermarket_id = row["id"]

    norm_name = normalize_text(title)
    clean_ean = ean.strip() if ean and ean.strip() else None
    parsed_brand, parsed_size = infer_brand_and_size(title, brand)
    canonical_key = build_canonical_key(title, parsed_brand, parsed_size)
    ing_key, d_tags = infer_ingredient_and_diet_tags(title, category)

    product_id = None
    if clean_ean:
        p = conn.execute("SELECT id, brand, unit_size FROM products WHERE ean = ?", (clean_ean,)).fetchone()
        if p:
            product_id = p["id"]

    if product_id is None and canonical_key:
        p = conn.execute(
            "SELECT id, brand, unit_size FROM products WHERE canonical_key = ?", (canonical_key,)
        ).fetchone()
        if p:
            product_id = p["id"]

    if product_id is None:
        p = conn.execute(
            "SELECT id, brand, unit_size FROM products WHERE normalized_name = ?", (norm_name,)
        ).fetchone()
        if p:
            product_id = p["id"]

    if product_id is None:
        cur = conn.execute(
            """
            INSERT INTO products (ean, normalized_name, canonical_key, display_name, brand, unit_size, category, ingredient_key, diet_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (clean_ean, norm_name, canonical_key, title.strip(), parsed_brand, parsed_size, category.strip() or "General", ing_key, d_tags),
        )
        product_id = cur.lastrowid
    else:
        conn.execute(
            """
            UPDATE products
            SET brand = CASE WHEN brand = '' THEN ? ELSE brand END,
                unit_size = CASE WHEN unit_size = '' THEN ? ELSE unit_size END,
                canonical_key = CASE WHEN canonical_key = '' THEN ? ELSE canonical_key END,
                ingredient_key = CASE WHEN ingredient_key = '' THEN ? ELSE ingredient_key END,
                diet_tags = CASE WHEN diet_tags = '' THEN ? ELSE diet_tags END
            WHERE id = ?
            """,
            (parsed_brand, parsed_size, canonical_key, ing_key, d_tags, product_id),
        )

    now = utc_now_iso()
    existing_offer = conn.execute(
        "SELECT id, price FROM offers WHERE supermarket_id = ? AND external_id = ?",
        (supermarket_id, str(external_id)),
    ).fetchone()

    if existing_offer:
        offer_id = existing_offer["id"]
        conn.execute(
            """
            UPDATE offers
            SET product_id = ?, title = ?, price = ?, list_price = ?,
                in_stock = ?, url = ?, image_url = ?, last_scraped_at = ?
            WHERE id = ?
            """,
            (
                product_id,
                title.strip(),
                float(price),
                float(list_price) if list_price else None,
                1 if in_stock else 0,
                url,
                image_url,
                now,
                offer_id,
            ),
        )
        if abs(existing_offer["price"] - float(price)) > 0.01:
            conn.execute(
                "INSERT INTO price_history (offer_id, price, recorded_at) VALUES (?, ?, ?)",
                (offer_id, float(price), now),
            )
    else:
        cur = conn.execute(
            """
            INSERT INTO offers (
                supermarket_id, product_id, external_id, title, price, list_price,
                currency, in_stock, url, image_url, last_scraped_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'UYU', ?, ?, ?, ?)
            """,
            (
                supermarket_id,
                product_id,
                str(external_id),
                title.strip(),
                float(price),
                float(list_price) if list_price else None,
                1 if in_stock else 0,
                url,
                image_url,
                now,
            ),
        )
        offer_id = cur.lastrowid
        conn.execute(
            "INSERT INTO price_history (offer_id, price, recorded_at) VALUES (?, ?, ?)",
            (offer_id, float(price), now),
        )
