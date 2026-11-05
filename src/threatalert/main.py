import argparse
import logging
import os

from dotenv import load_dotenv

from threatalert.config import load_config
from threatalert.experts.exposure import ExposureExpert
from threatalert.experts.severity import SeverityExpert
from threatalert.experts.urgency import UrgencyExpert
from threatalert.graph import build_graph
from threatalert.ingestion.rss import RSSSource
from threatalert.llm import LLMClient
from threatalert.notifiers import ConsoleNotifier, Notifier, SlackNotifier
from threatalert.store import SQLiteStore

EXPERTS = {
    "severity": SeverityExpert,
    "urgency": UrgencyExpert,
    "exposure": ExposureExpert,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create threat alerts from cybersecurity news.")
    parser.add_argument("--config", default="config/config.yaml", help="Path to the YAML config file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    load_dotenv()

    config = load_config(args.config)

    notifiers: list[Notifier] = [ConsoleNotifier()]
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        notifiers.append(SlackNotifier(webhook_url))

    graph = build_graph(
        sources=[RSSSource(feed.name, feed.url) for feed in config.feeds],
        store=SQLiteStore(os.getenv("DB_PATH", config.db_path)),
        llm=LLMClient(config.models),
        experts=[EXPERTS[name]() for name in config.experts],
        notifiers=notifiers,
        config=config,
    )
    final = graph.invoke(
        {"articles": [], "results": []},
        config={"max_concurrency": config.max_concurrency},
    )

    for result in final["results"]:
        average = "-" if result.average is None else f"{result.average:.2f}"
        print(result.status, "|", average, "|", result.scores, "|", result.article.title)
    print(len(final["results"]), "articles processed")


if __name__ == "__main__":
    main()
