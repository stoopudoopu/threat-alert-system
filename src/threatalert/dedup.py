from threatalert.models import Article
from threatalert.store import SQLiteStore


def filter_new(articles: list[Article], store: SQLiteStore) -> list[Article]:
    new_articles = []
    ids_in_this_run = set()
    for article in articles:
        if article.id in ids_in_this_run or store.is_seen(article.id):
            continue
        ids_in_this_run.add(article.id)
        new_articles.append(article)
    return new_articles

