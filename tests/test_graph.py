import anthropic
import httpx

from threatalert.config import Config
from threatalert.experts.exposure import ExposureExpert
from threatalert.experts.severity import SeverityExpert
from threatalert.experts.urgency import UrgencyExpert
from threatalert.graph import build_graph
from threatalert.ingestion.base import Source
from threatalert.llm import LLMOutputError
from threatalert.models import AlertDraft, Article, ClientProfile, DeepRelevance, Relevance, Score
from threatalert.notifiers import Notifier
from threatalert.store import SQLiteStore


class FakeSource(Source):
    name = "fake"

    def __init__(self, titles):
        self.titles = titles

    def fetch_articles(self):
        return [
            Article(id=title, source="fake", title=title, link="http://x", summary=title, published=None)
            for title in self.titles
        ]


class FakeLLM:
    """Decides its answer from keywords in the article title."""

    def __init__(self):
        self.calls = 0

    def parse(self, role, system, prompt, schema):
        self.calls += 1
        if "REFUSED" in prompt:
            raise LLMOutputError("refused")
        if "NETWORK" in prompt:
            raise anthropic.APIConnectionError(request=httpx.Request("POST", "http://x"))
        if schema is Relevance:
            if "IRRELEVANT" in prompt:
                return Relevance(reasoning="test", verdict="no")
            if "UNSURE" in prompt:
                return Relevance(reasoning="test", verdict="unsure")
            return Relevance(reasoning="test", verdict="yes")
        if schema is DeepRelevance:
            verdict = "no" if "DEEPNO" in prompt else "yes"
            return DeepRelevance(reasoning="test", verdict=verdict)
        if schema is AlertDraft:
            if "UNDRAFTABLE" in prompt:
                raise LLMOutputError("refused")
            return AlertDraft(summary="Drafted summary", why_it_matters="It matters", actions=["Patch"])
        return Score(reasoning="test", score=2 if "LOW" in prompt else 9)


class FakeNotifier(Notifier):
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def send(self, message):
        if self.fail:
            raise RuntimeError("delivery failed")
        self.sent.append(message)


def run(titles, tmp_path, llm=None, max_articles_per_run=100, notifier=None):
    store = SQLiteStore(str(tmp_path / "test.db"))
    config = Config(
        threshold=7.0,
        db_path="unused",
        feeds=[],
        client=ClientProfile(name="Acme", tech_stack=["GitLab"], description="A company"),
        models={},
        max_concurrency=3,
        max_articles_per_run=max_articles_per_run,
        experts=["severity", "urgency", "exposure"],
    )
    graph = build_graph(
        sources=[FakeSource(titles)],
        store=store,
        llm=llm or FakeLLM(),
        experts=[SeverityExpert(), UrgencyExpert(), ExposureExpert()],
        notifiers=[notifier or FakeNotifier()],
        config=config,
    )
    final = graph.invoke({"articles": [], "results": []}, config={"max_concurrency": 3})
    return {result.article.id: result for result in final["results"]}, store


def test_each_path_gets_the_right_status(tmp_path):
    results, _ = run(["HIGH", "IRRELEVANT", "UNSURE high", "UNSURE DEEPNO", "LOW"], tmp_path)

    assert results["HIGH"].status == "alert"
    assert results["HIGH"].average == 9
    assert results["IRRELEVANT"].status == "irrelevant"
    assert results["UNSURE high"].status == "alert"
    assert results["UNSURE DEEPNO"].status == "irrelevant"
    assert results["LOW"].status == "below_threshold"


def test_failure_in_one_branch_does_not_stop_the_others(tmp_path):
    results, _ = run(["HIGH", "REFUSED", "NETWORK"], tmp_path)

    assert results["HIGH"].status == "alert"
    assert results["REFUSED"].status == "failed"
    assert results["NETWORK"].status == "failed_retryable"


def test_only_temporary_failures_stay_unseen(tmp_path):
    _, store = run(["HIGH", "REFUSED", "NETWORK"], tmp_path)

    assert store.is_seen("HIGH")
    assert store.is_seen("REFUSED")
    assert not store.is_seen("NETWORK")


def test_second_run_makes_no_llm_calls(tmp_path):
    llm = FakeLLM()
    run(["HIGH"], tmp_path, llm)
    calls_after_first_run = llm.calls

    results, _ = run(["HIGH"], tmp_path, llm)

    assert results == {}
    assert llm.calls == calls_after_first_run


def test_no_new_articles_finishes_without_error(tmp_path):
    results, _ = run(["HIGH"], tmp_path)
    assert "HIGH" in results

    again, _ = run(["HIGH"], tmp_path)

    assert again == {}


def test_max_articles_per_run_limits_the_batch(tmp_path):
    results, store = run(["A", "B", "C"], tmp_path, max_articles_per_run=2)

    assert len(results) == 2
    assert not store.is_seen("C")


def test_unknown_error_is_retried(tmp_path):
    class BrokenLLM:
        def parse(self, role, system, prompt, schema):
            raise TypeError("Could not resolve authentication method")

    results, store = run(["HIGH"], tmp_path, BrokenLLM())

    assert results["HIGH"].status == "failed_retryable"
    assert not store.is_seen("HIGH")


def test_alert_is_drafted_and_sent_only_above_threshold(tmp_path):
    notifier = FakeNotifier()

    run(["HIGH", "LOW", "IRRELEVANT"], tmp_path, notifier=notifier)

    assert len(notifier.sent) == 1
    assert "THREAT ALERT: HIGH" in notifier.sent[0]
    assert "Drafted summary" in notifier.sent[0]


def test_alert_is_not_sent_twice(tmp_path):
    notifier = FakeNotifier()

    run(["HIGH"], tmp_path, notifier=notifier)
    run(["HIGH"], tmp_path, notifier=notifier)

    assert len(notifier.sent) == 1


def test_failed_delivery_is_retried_without_new_llm_calls(tmp_path):
    llm = FakeLLM()
    run(["HIGH"], tmp_path, llm, notifier=FakeNotifier(fail=True))
    calls_after_first_run = llm.calls
    notifier = FakeNotifier()

    run(["HIGH"], tmp_path, llm, notifier=notifier)

    assert len(notifier.sent) == 1
    assert llm.calls == calls_after_first_run


def test_refused_draft_still_sends_a_fallback_alert(tmp_path):
    notifier = FakeNotifier()

    results, _ = run(["HIGH UNDRAFTABLE"], tmp_path, notifier=notifier)

    assert results["HIGH UNDRAFTABLE"].status == "alert"
    assert "Review the source article." in notifier.sent[0]
