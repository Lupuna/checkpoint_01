import json
from datetime import date
from pathlib import Path


def load_kb(kb_dir: Path) -> list[dict]:
    docs = []
    for path in sorted(kb_dir.glob("*.md")):
        title, _, body = path.read_text(encoding="utf-8").partition("\n\n")
        docs.append({"id": path.stem, "title": title.lstrip("# ").strip(), "text": body.strip()})
    return docs


def load_orders(orders_path: Path) -> tuple[date, dict[int, dict]]:
    data = json.loads(orders_path.read_text(encoding="utf-8"))
    return date.fromisoformat(data["today"]), {order["order_id"]: order for order in data["orders"]}
