import re
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import ScrapedProduct, SupermarketAdapter


def parse_uyu_price(text: str) -> float | None:
    """Extrae un precio numérico desde cadenas como '$ 149,00', '$U 1.250' o '$ 200 $ 188' (oferta)."""
    if not text:
        return None
    # Buscar tokens numéricos individuales para no concatenar precio lista + precio oferta
    tokens = re.findall(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?", text)
    values: list[float] = []
    for tok in tokens:
        cleaned = tok
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts[-1]) == 3:
                cleaned = cleaned.replace(".", "")
        try:
            val = float(cleaned)
            if 5.0 <= val <= 45000.0:
                values.append(val)
        except ValueError:
            continue
    if not values:
        return None
    return min(values)


class PlaywrightSearchAdapter(SupermarketAdapter):
    """
    Adaptador configurable con Playwright para sitios con renderizado JS
    (por ejemplo Tienda Inglesa, Frog o El Dorado).
    """

    def __init__(
        self,
        slug: str,
        name: str,
        base_url: str,
        search_url_template: str,
        card_selector: str,
        title_selector: str,
        price_selector: str,
        link_selector: str = "a",
        image_selector: str = "img",
        brand_selector: str = "",
    ):
        self.slug = slug
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.search_url_template = search_url_template
        self.card_selector = card_selector
        self.title_selector = title_selector
        self.price_selector = price_selector
        self.link_selector = link_selector
        self.image_selector = image_selector
        self.brand_selector = brand_selector

    async def search(self, query: str, limit: int = 20) -> list[ScrapedProduct]:
        from playwright.async_api import async_playwright

        url = self.search_url_template.format(query=quote(query))
        results: list[ScrapedProduct] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                locale="es-UY",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                try:
                    await page.wait_for_selector(self.card_selector, timeout=8000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
                html = await page.content()
            finally:
                await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.card_selector)[:limit]

        for idx, card in enumerate(cards):
            title = ""
            for t_el in card.select(self.title_selector):
                candidate = t_el.get_text(" ", strip=True)
                candidate = candidate.replace("Agregar/Quitar de Favoritos", "").strip()
                if candidate:
                    title = candidate
                    break

            price_el = card.select_one(self.price_selector)
            if not title or not price_el:
                continue
            price = parse_uyu_price(price_el.get_text(" ", strip=True))
            if not title or not price:
                continue

            link_el = card.select_one(self.link_selector)
            href = link_el.get("href", "") if link_el else ""
            if href and href.startswith("/"):
                href = f"{self.base_url}{href}"
            elif not href:
                href = url

            img_el = card.select_one(self.image_selector)
            img_url = ""
            if img_el:
                for attr in ("data-src", "data-original", "data-lazy", "src"):
                    val = img_el.get(attr, "")
                    if val and not val.startswith("data:"):
                        img_url = val
                        break
            if img_url and img_url.startswith("/"):
                img_url = f"{self.base_url}{img_url}"

            brand_val = ""
            if self.brand_selector:
                b_el = card.select_one(self.brand_selector)
                if b_el:
                    brand_val = b_el.get_text(" ", strip=True)

            results.append(
                ScrapedProduct(
                    external_id=f"{self.slug}-{abs(hash(href + title)) % 10**10}-{idx}",
                    title=title,
                    price=price,
                    url=href,
                    brand=brand_val,
                    image_url=img_url,
                )
            )
        return results
