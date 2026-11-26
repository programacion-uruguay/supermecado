import httpx
from urllib.parse import quote
from typing import Optional
from .base import ScrapedProduct, SupermarketAdapter


class VtexAdapter(SupermarketAdapter):
    """Adaptador para supermercados en Uruguay que usan VTEX (ej. Disco, Devoto, Géant, Tata)."""

    def __init__(self, slug: str, name: str, base_url: str):
        self.slug = slug
        self.name = name
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, limit: int = 20) -> list[ScrapedProduct]:
        endpoint = f"{self.base_url}/api/catalog_system/pub/products/search/{quote(query)}"
        params = {"_from": 0, "_to": max(0, limit - 1)}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(endpoint, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results: list[ScrapedProduct] = []
        if not isinstance(data, list):
            return results

        for item in data:
            parsed = self._parse_vtex_item(item)
            if parsed:
                results.append(parsed)
        return results

    def _parse_vtex_item(self, item: dict) -> Optional[ScrapedProduct]:
        items = item.get("items") or []
        if not items:
            return None

        sku = items[0]
        sellers = sku.get("sellers") or []
        if not sellers:
            return None

        offer = sellers[0].get("commertialOffer") or {}
        price = offer.get("Price")
        if not price or float(price) <= 0:
            return None

        list_price = offer.get("ListPrice")
        available = int(offer.get("AvailableQuantity") or 0) > 0
        images = sku.get("images") or []
        image_url = images[0].get("imageUrl", "") if images else ""
        categories = item.get("categories") or []
        category = categories[0].strip("/").split("/")[-1] if categories else "General"
        link = item.get("link") or f"{self.base_url}/{item.get('linkText', '')}/p"

        return ScrapedProduct(
            external_id=str(item.get("productId") or sku.get("itemId")),
            title=item.get("productName") or sku.get("nameComplete") or "Sin nombre",
            price=float(price),
            list_price=float(list_price) if list_price and float(list_price) > float(price) else None,
            url=link,
            ean=sku.get("ean"),
            brand=item.get("brand") or "",
            category=category,
            in_stock=available,
            image_url=image_url,
        )
