from abc import ABC, abstractmethod
from pathlib import Path
import sqlite3

class Store(ABC):
    @abstractmethod
    def is_seen(self, article_id: str) -> bool:
        ...
    
    @abstractmethod
    def mark_seen(self, article_id: str) -> None:
        ...

class SQLiteStore(Store):
    def __init__(self, path: str):
        self.path = Path(path)
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
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
