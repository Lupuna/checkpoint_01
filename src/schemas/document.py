from pydantic import BaseModel, Field


class DocumentIn(BaseModel):
    file: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    description: str


class DocumentOut(DocumentIn):
    id: int


class ChunkIn(BaseModel):
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    text: str = Field(min_length=1)
    vector: list[float]
