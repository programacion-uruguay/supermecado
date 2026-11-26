from .base import ScrapedProduct, SupermarketAdapter
from .vtex import VtexAdapter
from .playwright_generic import PlaywrightSearchAdapter
from .redmarket5 import RedMarket5Adapter

__all__ = [
    "ScrapedProduct",
    "SupermarketAdapter",
    "VtexAdapter",
    "PlaywrightSearchAdapter",
    "RedMarket5Adapter",
]
