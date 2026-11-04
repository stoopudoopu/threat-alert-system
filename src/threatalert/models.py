from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

class Article(BaseModel):
    id: str
    source: str
    title: str
    link: str
    summary: str
    content: str = ""
    published: datetime | None
    cves: list[str] = []

class ClientProfile(BaseModel):
    name: str
    tech_stack: list[str]
    description: str

class Score(BaseModel):
    reasoning: str
    score: int = Field(ge=0, le=10)

class Relevance(BaseModel):
    reasoning: str
    verdict: Literal["yes", "no", "unsure"]

class DeepRelevance(BaseModel):
    reasoning: str
    verdict: Literal["yes", "no"]

