from datetime import datetime
from pydantic import BaseModel

class Article(BaseModel):
    id: str
    source: str
    title: str
    link: str
    summary: str
    content: str = ""
    published: datetime | None
    cves: list[str] = []

    

