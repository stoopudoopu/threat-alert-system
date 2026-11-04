from abc import ABC, abstractmethod
from pathlib import Path
from threatalert.models import Article
import sqlite3
import json

class Store(ABC):
    @abstractmethod
    def is_seen(self, article_id: str) -> bool:
        ...
    
    @abstractmethod
    def mark_seen(self, article_id: str) -> None:
        ...

    @abstractmethod
    def save_article(self, article: Article) -> None:
        ...

class SQLiteStore(Store):
    def __init__(self, path: str):
        self.path = Path(path)
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                source TEXT,
                title TEXT,
                link TEXT,
                summary TEXT,
                content TEXT,
                published TEXT,
                cves TEXT
            )
        """)
        conn.commit()
        conn.close()

    def is_seen(self, article_id: str) -> bool:
        conn = sqlite3.connect(self.path)
        row = conn.execute("SELECT 1 FROM seen WHERE id = ?", (article_id,)).fetchone()
        conn.close()
        return row is not None

    def mark_seen(self, article_id: str) -> None:
        conn = sqlite3.connect(self.path)
        conn.execute("INSERT OR IGNORE INTO seen (id) VALUES (?)", (article_id,))
        conn.commit()
        conn.close()

    def save_article(self, article: Article) -> None:
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT OR IGNORE INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                article.id,
                article.source,
                article.title,
                article.link,
                article.summary,
                article.content,
                article.published.isoformat() if article.published else None,
                json.dumps(article.cves),
            ),
        )
        conn.commit()
        conn.close()
