import copy
import inspect
import json
from collections.abc import Callable
from datetime import date
from enum import StrEnum

from pydantic import ValidationError

from src.services.document import DocumentService
from src.tools.definitions import TOOL_ARGS

REFUND_DAYS = 14


class OrderStatus(StrEnum):
    PLACED = "placed"
    ASSEMBLED = "assembled"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


NOT_SHIPPED = (OrderStatus.PLACED, OrderStatus.ASSEMBLED)


class OrderTools:
    def __init__(self, orders: dict[int, dict], today: date, document_service: DocumentService | None = None):
        self.document_service = document_service
        self._original = orders
        self.today = today
        self.orders: dict[int, dict] = {}
        self.refunds: list[dict] = []
        self.reset()

    @property
    def handlers(self) -> dict[str, Callable[..., dict]]:
        handlers = {
            "get_order": self.get_order,
            "cancel_order": self.cancel_order,
            "change_address": self.change_address,
            "create_refund": self.create_refund,
        }
        if self.document_service is not None:
            handlers["search_docs"] = self.search_docs
        return handlers

    def reset(self) -> None:
        self.orders.clear()
        self.orders.update(copy.deepcopy(self._original))
        self.refunds.clear()

    async def run(self, name: str, arguments_json: str) -> str:
        handler = self.handlers.get(name)
        if handler is None:
            result = {"error": f"Неизвестный инструмент: {name}", "hint": "Ответьте клиенту без этого инструмента"}
        else:
            try:
                args = TOOL_ARGS[name].model_validate_json(arguments_json)
            except ValidationError as e:
                result = {"error": f"Неверные аргументы: {e.errors(include_url=False)}",
                          "hint": "Вызовите инструмент заново с аргументами по схеме"}
            else:
                result = handler(**args.model_dump())
                if inspect.isawaitable(result):
                    result = await result
        return json.dumps(result, ensure_ascii=False)

    def get_order(self, order_id: int) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            return self._not_found(order_id)

        result = {**order, "refunded_rub": self._refunded(order_id)}
        if order["delivered_at"]:
            result["days_since_delivery"] = self._days_since_delivery(order)
        return result

    def cancel_order(self, order_id: int, reason: str) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            return self._not_found(order_id)

        if order.get("custom_build") and order.get("build_started"):
            return {"error": "Индивидуальная сборка уже начата, заказ нельзя отменить",
                    "hint": "Предложите передать обращение оператору"}

        match order["status"]:
            case OrderStatus.CANCELLED:
                return {"error": "Заказ уже отменён", "hint": "Сообщите клиенту, что заказ уже отменён"}
            case OrderStatus.IN_TRANSIT:
                return {"error": "Заказ уже передан в доставку",
                        "hint": "Предложите отказаться от заказа при получении, деньги вернутся"}
            case OrderStatus.DELIVERED:
                return {"error": "Заказ уже получен", "hint": "Предложите оформить возврат"}
            case status if status not in NOT_SHIPPED:
                return {"error": f"Отмена невозможна в статусе {status}",
                        "hint": "Предложите передать обращение оператору"}

        order["status"] = OrderStatus.CANCELLED.value
        result = {"order_id": order_id, "status": order["status"]}
        if order["paid_rub"] > 0:
            result["refund"] = self._add_refund(order_id, order["paid_rub"], reason)
        return result

    def change_address(self, order_id: int, address: str) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            return self._not_found(order_id)

        match order["status"]:
            case OrderStatus.CANCELLED:
                return {"error": "Заказ отменён", "hint": "Предложите оформить новый заказ на нужный адрес"}
            case OrderStatus.IN_TRANSIT:
                return {"error": "Заказ уже передан в доставку, адрес изменить нельзя",
                        "hint": "Предложите отказаться при получении и оформить заказ заново на новый адрес"}
            case OrderStatus.DELIVERED:
                return {"error": "Заказ уже получен", "hint": "Сообщите клиенту, что заказ уже доставлен"}
            case status if status not in NOT_SHIPPED:
                return {"error": f"Адрес нельзя изменить в статусе {status}",
                        "hint": "Предложите передать обращение оператору"}

        order["address"] = address
        return {"order_id": order_id, "status": order["status"], "address": address}

    def create_refund(self, order_id: int, amount_rub: int, reason: str) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            return self._not_found(order_id)

        match order["status"]:
            case OrderStatus.CANCELLED:
                return {"error": "Заказ отменён, деньги по нему уже возвращены при отмене",
                        "hint": "Сообщите клиенту, что возврат оформлен при отмене"}
            case status if status in NOT_SHIPPED:
                return {"error": "Заказ ещё не передан в доставку", "hint": "Предложите отменить заказ"}
            case status if status != OrderStatus.DELIVERED:
                return {"error": "Заказ ещё не получен, возврат оформляется после получения",
                        "hint": "Предложите отказаться от заказа при получении, деньги вернутся"}

        days = self._days_since_delivery(order)
        if days > REFUND_DAYS:
            return {"error": f"С получения прошло {days} дней, возврат возможен только в течение {REFUND_DAYS}",
                    "hint": "Если товар неисправен, предложите обратиться по гарантии"}

        available = order["paid_rub"] - self._refunded(order_id)
        if available <= 0:
            return {"error": "По заказу уже возвращена вся оплаченная сумма",
                    "hint": "Сообщите клиенту, что возврат уже оформлен"}
        if not 0 < amount_rub <= available:
            return {"error": f"Можно вернуть от 1 до {available} ₽",
                    "hint": f"Предложите возврат на сумму до {available} ₽"}

        return {"order_id": order_id, "refund": self._add_refund(order_id, amount_rub, reason)}

    async def search_docs(self, query: str) -> dict:
        chunks = await self.document_service.hybrid_search(query, k=5)
        return {"fragments": [
            {
                "source": c["title"],
                "pages": f"{c['page_start']}" if c["page_start"] == c["page_end"] else f"{c['page_start']}–{c['page_end']}",
                "text": c["text"].replace("###", "\n"),
            }
            for c in chunks
        ]}

    @staticmethod
    def _not_found(order_id: int) -> dict:
        return {"error": f"Заказ {order_id} не найден", "hint": "Попросите клиента проверить номер заказа"}

    def _days_since_delivery(self, order: dict) -> int:
        return (self.today - date.fromisoformat(order["delivered_at"])).days

    def _refunded(self, order_id: int) -> int:
        return sum(r["amount_rub"] for r in self.refunds if r["order_id"] == order_id)

    def _add_refund(self, order_id: int, amount_rub: int, reason: str) -> dict:
        refund = {
            "refund_id": f"R-{len(self.refunds) + 1}",
            "order_id": order_id,
            "amount_rub": amount_rub,
            "reason": reason,
        }
        self.refunds.append(refund)
        return refund
