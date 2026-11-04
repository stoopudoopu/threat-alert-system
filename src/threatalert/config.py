from pathlib import Path
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


def load_config(path: str) -> Config:
    text = Path(path).read_text()
    data = yaml.safe_load(text)
    return Config.model_validate(data)
