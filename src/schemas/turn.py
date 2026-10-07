from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class TurnItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "message"
    role: Role | None = None


class Turn(BaseModel):
    items: list[TurnItem]

    @model_validator(mode="after")
    def calls_have_outputs(self) -> "Turn":
        calls = {item.call_id for item in self.items if item.type == "function_call"}
        outputs = {item.call_id for item in self.items if item.type == "function_call_output"}
        if calls != outputs:
            raise ValueError(f"вызовы без результата {calls - outputs}, результаты без вызова {outputs - calls}")
        return self
