import json
import sqlite3
from datetime import datetime, timezone

from threatalert.models import Article


class SQLiteStore:
    def __init__(self, path: str):
        self.path = path
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                article_id TEXT,
                client TEXT,
                message TEXT,
                sent_at TEXT,
                UNIQUE (article_id, client)
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

    def save_alert(self, article_id: str, client: str, message: str) -> None:
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT OR IGNORE INTO alerts (article_id, client, message) VALUES (?, ?, ?)",
            (article_id, client, message),
        )
        conn.commit()
        conn.close()

    def unsent_alerts(self) -> list[tuple[str, str, str]]:
        conn = sqlite3.connect(self.path)
        rows = conn.execute(
            "SELECT article_id, client, message FROM alerts WHERE sent_at IS NULL"
        ).fetchall()
        conn.close()
        return rows

    def mark_alert_sent(self, article_id: str, client: str) -> None:
        conn = sqlite3.connect(self.path)
        conn.execute(
            "UPDATE alerts SET sent_at = ? WHERE article_id = ? AND client = ?",
            (datetime.now(timezone.utc).isoformat(), article_id, client),
        )
        conn.commit()
        conn.close()
