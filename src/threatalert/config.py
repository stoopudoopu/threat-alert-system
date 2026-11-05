from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from threatalert.models import ClientProfile


class FeedConfig(BaseModel):
    name: str
    url: str


class Config(BaseModel):
    threshold: float = Field(ge=0, le=10)
    db_path: str
    feeds: list[FeedConfig]
    client: ClientProfile
    models: dict[str, str]
    max_concurrency: int = Field(ge=1)
    max_articles_per_run: int = Field(ge=1)
    experts: list[Literal["severity", "urgency", "exposure"]] = Field(min_length=1)


def load_config(path: str) -> Config:
    text = Path(path).read_text()
    data = yaml.safe_load(text)
    return Config.model_validate(data)
