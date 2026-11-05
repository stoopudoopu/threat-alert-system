import logging
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import ValidationError

from threatalert.alerting import draft_alert, format_alert, should_alert
from threatalert.config import Config
from threatalert.dedup import filter_new
from threatalert.experts.base import Expert
from threatalert.ingestion.base import Source, collect_articles
from threatalert.llm import LLMClient, LLMOutputError
from threatalert.models import Article, ArticleResult
from threatalert.notifiers import Notifier
from threatalert.prefilter import is_relevant
from threatalert.scoring import average_score
from threatalert.store import SQLiteStore
from threatalert.text import extract_cves

logger = logging.getLogger(__name__)

PERMANENT_ERRORS = (LLMOutputError, ValidationError)


class GraphState(TypedDict):
    articles: list[Article]
    results: Annotated[list[ArticleResult], operator.add]


def analyze_article(article: Article, config: Config, llm: LLMClient, experts: list[Expert]) -> ArticleResult:
    if not is_relevant(article, config.client, llm):
        return ArticleResult(article=article, status="irrelevant")

    scores = [expert.score(article, config.client, llm) for expert in experts]
    average = average_score(scores)
    alert = should_alert(average, config.threshold)
    return ArticleResult(
        article=article,
        status="alert" if alert else "below_threshold",
        scores={expert.name: score.score for expert, score in zip(experts, scores)},
        average=average,
        draft=draft_alert(article, config.client, llm) if alert else None,
    )


def build_graph(
    sources: list[Source],
    store: SQLiteStore,
    llm: LLMClient,
    experts: list[Expert],
    notifiers: list[Notifier],
    config: Config,
):
    def ingest(state: GraphState) -> dict:
        return {"articles": collect_articles(sources)}

    def dedup(state: GraphState) -> dict:
        new_articles = filter_new(state["articles"], store)
        return {"articles": new_articles[: config.max_articles_per_run]}

    def enrich(state: GraphState) -> dict:
        for article in state["articles"]:
            article.cves = extract_cves(f"{article.title} {article.summary} {article.content}")
            store.save_article(article)
        return {"articles": state["articles"]}

    def fan_out(state: GraphState):
        if not state["articles"]:
            return "deliver"  # alerts that failed to send earlier still get retried
        return [Send("process_article", {"article": article}) for article in state["articles"]]

    def process_article(payload: dict) -> dict:
        article = payload["article"]
        try:
            result = analyze_article(article, config, llm, experts)
        except PERMANENT_ERRORS:
            logger.exception("Permanent failure: %s", article.id)
            result = ArticleResult(article=article, status="failed")
        except Exception:
            logger.exception("Failure, will retry next run: %s", article.id)
            result = ArticleResult(article=article, status="failed_retryable")
        return {"results": [result]}

    def deliver(state: GraphState) -> dict:
        client = config.client.name
        for result in state["results"]:
            if result.status == "alert":
                message = format_alert(result.article, result.draft, result.average)
                store.save_alert(result.article.id, client, message)
            if result.status != "failed_retryable":
                store.mark_seen(result.article.id)

        for article_id, alert_client, message in store.unsent_alerts():
            try:
                for notifier in notifiers:
                    notifier.send(message)
            except Exception:
                logger.exception("Could not send alert, will retry next run: %s", article_id)
            else:
                store.mark_alert_sent(article_id, alert_client)
        return {}

    builder = StateGraph(GraphState)
    builder.add_node("ingest", ingest)
    builder.add_node("dedup", dedup)
    builder.add_node("enrich", enrich)
    builder.add_node("process_article", process_article)
    builder.add_node("deliver", deliver)
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "dedup")
    builder.add_edge("dedup", "enrich")
    builder.add_conditional_edges("enrich", fan_out, ["process_article", "deliver"])
    builder.add_edge("process_article", "deliver")
    builder.add_edge("deliver", END)
    return builder.compile()
