from pydantic import BaseModel

from src.config import (
    PRICE_CACHE_WRITE_PER_1M,
    PRICE_CACHED_PER_1M,
    PRICE_INPUT_PER_1M,
    PRICE_OUTPUT_PER_1M,
)


class Usage(BaseModel):
    steps: int = 0
    input: int = 0
    cached: int = 0
    cache_write: int = 0
    output: int = 0
    reasoning: int = 0

    def add(self, usage) -> None:
        self.steps += 1
        if usage is None:
            return
        details_in = getattr(usage, "input_tokens_details", None)
        details_out = getattr(usage, "output_tokens_details", None)
        self.input += usage.input_tokens
        self.cached += getattr(details_in, "cached_tokens", 0) or 0
        self.cache_write += getattr(details_in, "cache_write_tokens", 0) or 0
        self.output += usage.output_tokens
        self.reasoning += getattr(details_out, "reasoning_tokens", 0) or 0

    def cost_usd(self) -> float | None:
        prices = (PRICE_INPUT_PER_1M, PRICE_CACHED_PER_1M, PRICE_CACHE_WRITE_PER_1M, PRICE_OUTPUT_PER_1M)
        if None in prices:
            return None
        price_in, price_cached, price_cache_write, price_out = prices
        ordinary = self.input - self.cached - self.cache_write
        total = (
            ordinary * price_in
            + self.cached * price_cached
            + self.cache_write * price_cache_write
            + self.output * price_out
        )
        return round(total / 1_000_000, 6)

    def report(self) -> dict:
        return {**self.model_dump(), "cost_usd": self.cost_usd()}
