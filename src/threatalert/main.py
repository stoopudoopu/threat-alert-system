import logging

from threatalert.config import load_config
from threatalert.ingestion.base import collect_articles
from threatalert.ingestion.rss import RSSSource
from threatalert.dedup import filter_new
from threatalert.store import SQLiteStore
from threatalert.prefilter import extract_cves

def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config("config/config.yaml")
    sources = [RSSSource(feed.name, feed.url) for feed in config.feeds]
    articles = collect_articles(sources)
    store = SQLiteStore(config.db_path)
    new_articles = filter_new(articles, store)
    print(len(articles), "read,", len(new_articles), "new")

    for article in new_articles:
        article.cves = extract_cves(f"{article.title} {article.summary} {article.content}")
        store.save_article(article)
        print(article.source, "|", article.title, "|", article.cves)
        store.mark_seen(article.id)  # provisional


if __name__ == "__main__":
    main()