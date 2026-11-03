import httpx
import feedparser
from threatalert.models import Article
from threatalert.ingestion.base import Source
from datetime import datetime, timezone


def fetch(url: str) -> bytes:
    response = httpx.get(url, timeout=20, follow_redirects=True)
    response.raise_for_status()
    return response.content

def parse(content: bytes, source: str) -> list[Article]:
    feed = feedparser.parse(content)
    if not feed.entries:
        raise ValueError("Empty feed, no entries found :(. The provided URL can't be parsed for some reason.")
    return [_to_article(entry, source) for entry in feed.entries]

def _to_datetime(parsed) -> datetime | None:
    if parsed is None:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)

def _to_article(entry, source: str) -> Article:
    return Article(
        id=entry.get("id") or entry.get("link"),
        source=source,
        title=entry.get("title", ""),
        link=entry.get("link"),
        summary=entry.get("summary", ""),
        published=_to_datetime(entry.get("published_parsed"))
    )

class RSSSource(Source):
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def fetch_articles(self) -> list[Article]:
        return parse(fetch(self.url), self.name)
