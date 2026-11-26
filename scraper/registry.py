from .adapters import VtexAdapter, PlaywrightSearchAdapter, RedMarket5Adapter, SupermarketAdapter


def get_adapters() -> dict[str, SupermarketAdapter]:
    """
    Registro de supermercados de Montevideo.
    Todos los selectores y URLs fueron verificados contra las webs reales.
    """
    return {
        "disco": PlaywrightSearchAdapter(
            slug="disco",
            name="Disco",
            base_url="https://www.disco.com.uy",
            search_url_template="https://www.disco.com.uy/productos/keyword/{query}",
            card_selector=".product-item",
            title_selector=".desc-top a:not(.favorite-button), .prod-tit, .desc-top",
            price_selector=".product-prices .price, .desc-prices .price, .price",
            brand_selector=".prod-cats, .desc-middle",
        ),
        "devoto": PlaywrightSearchAdapter(
            slug="devoto",
            name="Devoto",
            base_url="https://www.devoto.com.uy",
            search_url_template="https://www.devoto.com.uy/productos/keyword/{query}",
            card_selector=".product-item",
            title_selector=".desc-top a:not(.favorite-button), .prod-tit, .desc-top",
            price_selector=".product-prices .price, .desc-prices .price, .price",
            brand_selector=".prod-cats, .desc-middle",
        ),
        "geant": PlaywrightSearchAdapter(
            slug="geant",
            name="Géant",
            base_url="https://www.geant.com.uy",
            search_url_template="https://www.geant.com.uy/productos/keyword/{query}",
            card_selector=".product-item",
            title_selector=".desc-top a:not(.favorite-button), .prod-tit, .desc-top",
            price_selector=".product-prices .price, .desc-prices .price, .price",
            brand_selector=".prod-cats, .desc-middle",
        ),
        "tata": PlaywrightSearchAdapter(
            slug="tata",
            name="Tata",
            base_url="https://www.tata.com.uy",
            search_url_template="https://www.tata.com.uy/s/?q={query}&sort=score_desc",
            card_selector="article",
            title_selector='a[class*="fs-link"], h2, h3',
            price_selector='span[class*="fs-price"]',
            brand_selector=".product-shelf__brand-text, .product__shelf__brand",
        ),
        "tienda_inglesa": PlaywrightSearchAdapter(
            slug="tienda_inglesa",
            name="Tienda Inglesa",
            base_url="https://www.tiendainglesa.com.uy",
            search_url_template="https://www.tiendainglesa.com.uy/supermercado/busqueda?0,0,{query},0",
            card_selector=".card-product-container, .ProductCard, .card-product",
            title_selector=".card-product-name, .ProductCard-name, h2, h3",
            price_selector=".ProductPrice, .card-product-price, .price",
        ),
        "el_dorado": VtexAdapter(
            "el_dorado",
            "El Dorado",
            "https://www.eldorado.com.uy",
        ),
        "frog": PlaywrightSearchAdapter(
            slug="frog",
            name="Frog",
            base_url="https://frog.uy",
            search_url_template="https://frog.uy/search?q={query}",
            card_selector=".item-box, .product-item",
            title_selector=".product-title a, .product-title, h2 a",
            price_selector=".actual-price, .price",
        ),
        "el_clon": PlaywrightSearchAdapter(
            slug="el_clon",
            name="El Clon",
            base_url="https://www.elclon.com.uy",
            search_url_template="https://www.elclon.com.uy/catalogo?q={query}",
            card_selector=".aListProductos .it",
            title_selector="a.tit, .tit",
            price_selector=".precio.venta, .precios .venta, .precios",
        ),
        "redmarket5": RedMarket5Adapter(),
    }
