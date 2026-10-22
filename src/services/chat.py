from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from src.config import MAX_STEP, MODEL
from src.prompts.system import get_system_prompt
from src.schemas.message import MessageIn
from src.schemas.session import Session
from src.schemas.turn import Role, Turn
from src.schemas.usage import Usage
from src.services.session import SessionService
from src.tools.definitions import TOOLS
from src.tools.order_tools import OrderTools


class ChatService:
    FALLBACK = "Не получилось решить обращение, передаю его оператору"
    REFUSAL = "Ты спросил что-то нехорошее, атата так делать"

    def __init__(self, session_service: SessionService, aclient: AsyncOpenAI, order_tools: OrderTools):
        self.session_service = session_service
        self.aclient = aclient
        self.order_tools = order_tools
        self.system_prompt = get_system_prompt()

    async def chat(self, session: Session, message: MessageIn) -> AsyncIterator[tuple[str, object]]:
        history = [item.model_dump(mode="json", exclude_unset=True) for item in session.history]
        turn = [{"role": Role.USER, "content": message.text}]
        usage = Usage()

        for _ in range(MAX_STEP):
            stream = await self.aclient.responses.create(
                model=MODEL, instructions=self.system_prompt, input=[*history, *turn], tools=TOOLS, store=False,
                max_output_tokens=2000, reasoning={"effort": "low"}, stream=True,
                include=["reasoning.encrypted_content"],
            )

            done, final, refused = {}, None, False
            async with stream:
                async for event in stream:
                    if event.type == "response.output_text.delta":
                        yield "text", event.delta
                    elif event.type == "response.refusal.done":
                        refused = True
                    elif event.type == "response.output_item.done":
                        done[event.output_index] = event.item
                    elif event.type in ("response.completed", "response.incomplete"):
                        final = event.response

            if final is None:
                raise RuntimeError("стрим закончился без response.completed")
            usage.add(final.usage)

            output = [done[i] for i in sorted(done)]
            if refused or final.status == "incomplete":
                turn += [item.to_dict() for item in output if item.type != "function_call"]
                fallback = self.REFUSAL if refused else self.FALLBACK
                break

            turn += [item.to_dict() for item in output]
            calls = [item for item in output if item.type == "function_call"]
            if not calls:
                fallback = None
                break

            for call in calls:
                turn.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": await self.order_tools.run(call.name, call.arguments),
                })
        else:
            fallback = self.FALLBACK

        if fallback:
            yield "text", fallback
            turn.append({"role": Role.ASSISTANT, "content": fallback})

        await self.session_service.append_turn(session.id, Turn(items=turn))
        yield "usage", usage.report()
