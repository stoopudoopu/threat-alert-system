from abc import ABC, abstractmethod
from threatalert.models import Article
import logging

logger = logging.getLogger(__name__)

class Source(ABC):
    name: str

    @abstractmethod
    def fetch_articles(self) -> list[Article]:
        ...

def collect_articles(sources: list[Source]) -> list[Article]:
    articles = []
    for source in sources:
        try:
            articles.extend(source.fetch_articles())
        except Exception:
            logger.exception("Source failed: %s", source.name)
    if not articles:
        raise RuntimeError("All sources failed")
    return articles