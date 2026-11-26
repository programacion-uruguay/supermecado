import httpx
from .base import ScrapedProduct, SupermarketAdapter


class RedMarket5Adapter(SupermarketAdapter):
    """Adaptador directo a la API JSON pública de RedMarket5 (Montevideo)."""

    API_URL = "https://2jq5ktbom0.execute-api.sa-east-1.amazonaws.com/product"

    def __init__(self) -> None:
        self.slug = "redmarket5"
        self.name = "RedMarket5"
        self.base_url = "https://redmarket5.com.uy"

    async def search(self, query: str, limit: int = 20) -> list[ScrapedProduct]:
        params = {"sortBy": "name", "search": query.strip()}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(self.API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("items") or []
        results: list[ScrapedProduct] = []

        for item in items:
            if not item.get("isActive", True):
                continue
            title = (item.get("productName") or "").strip()
            if not title:
                continue

            price = float(item.get("finalPrice") or item.get("price") or 0)
            if price <= 0:
                continue

            base_price = float(item.get("price") or price)
            list_price = base_price if base_price > price else None
            barcode = str(item.get("barcode") or "").strip()
            ean = barcode if len(barcode) >= 8 and not barcode.startswith("0000000") else None
            prod_id = str(item.get("productId") or "")
            category = "Almacén" if item.get("categoryId") == "CAT-000001" else "General"

            results.append(
                ScrapedProduct(
                    external_id=prod_id or title,
                    title=title,
                    price=price,
                    list_price=list_price,
                    url=f"{self.base_url}/catalog",
                    ean=ean,
                    brand=(item.get("brand") or "").strip(),
                    category=category,
                    in_stock=int(item.get("stockActual") or 1) > 0,
                    image_url=item.get("image") or "",
                )
            )
            if len(results) >= limit:
                break

        return results
