import os
from pathlib import Path

from src.data_parser import load_orders

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_PATH = os.getenv("DB_PATH", "support.db")
MODEL = "gpt-5.6-luna"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMENSIONS = 1536
DATA_DIR = Path(__file__).parent.parent / "data"
INCOMING_DIR = DATA_DIR / "incoming"
ORDERS_PATH = DATA_DIR / "orders.json"

TODAY, ORDERS = load_orders(ORDERS_PATH)
MAX_STEP = 8


def price(name: str) -> float | None:
    value = os.getenv(name)
    return float(value) if value else None


PRICE_INPUT_PER_1M = price("PRICE_INPUT_PER_1M")
PRICE_CACHED_PER_1M = price("PRICE_CACHED_PER_1M")
PRICE_CACHE_WRITE_PER_1M = price("PRICE_CACHE_WRITE_PER_1M")
PRICE_OUTPUT_PER_1M = price("PRICE_OUTPUT_PER_1M")
