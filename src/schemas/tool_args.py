from pydantic import BaseModel, ConfigDict, Field


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetOrderArgs(ToolArgs):
    order_id: int = Field(description="Номер заказа из обращения клиента")


class CancelOrderArgs(GetOrderArgs):
    reason: str = Field(description="Причина отмены со слов клиента")


class ChangeAddressArgs(GetOrderArgs):
    address: str = Field(description="Новый адрес доставки целиком, как назвал клиент")


class CreateRefundArgs(GetOrderArgs):
    amount_rub: int = Field(description="Сумма возврата в рублях")
    reason: str = Field(description="Причина возврата со слов клиента")


class SearchDocsArgs(ToolArgs):
    query: str = Field(
        description="Поисковый запрос словами документа, а не клиента: «гарантийный срок бытовой техники», "
                    "а не «на мой заказ ещё действует гарантия?». Без номеров заказов и обращений к клиенту."
    )
