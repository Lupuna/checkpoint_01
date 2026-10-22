import json
from datetime import date
from pathlib import Path


def load_orders(orders_path: Path) -> tuple[date, dict[int, dict]]:
    data = json.loads(orders_path.read_text(encoding="utf-8"))
    return date.fromisoformat(data["today"]), {order["order_id"]: order for order in data["orders"]}
