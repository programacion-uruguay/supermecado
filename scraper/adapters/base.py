from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrapedProduct:
    external_id: str
    title: str
    price: float
    url: str
    ean: Optional[str] = None
    brand: str = ""
    category: str = "General"
    list_price: Optional[float] = None
    in_stock: bool = True
    image_url: str = ""


class SupermarketAdapter(ABC):
    slug: str
    name: str
    base_url: str

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[ScrapedProduct]:
        """Busca productos en la web del supermercado para un término dado."""
        raise NotImplementedError
