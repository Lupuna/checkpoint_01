from src.schemas.tool_args import (
    CancelOrderArgs,
    ChangeAddressArgs,
    CreateRefundArgs,
    GetOrderArgs,
    SearchDocsArgs,
    ToolArgs,
)

TOOL_ARGS: dict[str, type[ToolArgs]] = {
    "get_order": GetOrderArgs,
    "cancel_order": CancelOrderArgs,
    "change_address": ChangeAddressArgs,
    "create_refund": CreateRefundArgs,
    "search_docs": SearchDocsArgs,
}

DESCRIPTIONS = {
    "get_order": "Возвращает заказ по номеру: статус, состав, оплату, дату получения, сколько дней прошло с получения "
                 "и сколько уже возвращено. Вызывайте перед любым действием с заказом.",
    "cancel_order": "Отменяет заказ. Если заказ оплачен, автоматически оформляет возврат всей оплаченной суммы. "
                    "Вызывайте, только когда клиент прямо просит отменить заказ.",
    "change_address": "Меняет адрес доставки заказа. Вызывайте, только когда клиент назвал новый адрес полностью.",
    "create_refund": "Оформляет возврат денег по полученному заказу. Необратимое действие: вызывайте, только когда "
                     "клиент прямо просит вернуть деньги и сумма понятна.",
    "search_docs": "Ищет фрагменты документов магазина: регламента гарантийного обслуживания, правил программы "
                    "лояльности и справочника покупателя с руководствами к робот-пылесосу AquaVac R7 и смарт-часам "
                    "PulseOne S3. Возвращает до 5 фрагментов с названием документа и страницей. Вызывайте перед "
                    "любым ответом о гарантии, ремонте, бонусах, возврате, доставке и работе товаров. Если вопрос "
                    "про несколько тем, вызывайте по разу на каждую тему. Если ничего подходящего не нашлось, "
                    "попробуйте один раз переформулировать запрос.",
}


def _tool(name: str, args: type[ToolArgs]) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": DESCRIPTIONS[name],
        "parameters": args.model_json_schema(),
        "strict": True,
    }


TOOLS = [_tool(name, args) for name, args in TOOL_ARGS.items()]
