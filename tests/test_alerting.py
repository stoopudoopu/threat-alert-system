import httpx
import pytest
from fakes import FakeLLM

from threatalert.alerting import draft_alert, format_alert
from threatalert.models import AlertDraft, Article, ClientProfile
from threatalert.notifiers import SlackNotifier


def make_article():
    return Article(id="1", source="test", title="GitLab flaw", link="http://x/1", summary="A bug",
                   content="<p>Full text</p>", published=None, cves=["CVE-2026-1234"])


def test_draft_uses_the_drafting_model_and_clean_text():
    draft = AlertDraft(summary="s", why_it_matters="w", actions=["a"])
    llm = FakeLLM(draft)
    client = ClientProfile(name="Acme", tech_stack=["GitLab"], description="Long description")

    assert draft_alert(make_article(), client, llm) == draft
    assert llm.calls[0]["role"] == "drafting"
    assert "Long description" in llm.calls[0]["prompt"]
    assert "Full text" in llm.calls[0]["prompt"]
    assert "<p>" not in llm.calls[0]["prompt"]


def test_format_alert_includes_the_key_fields():
    draft = AlertDraft(summary="What happened", why_it_matters="Why", actions=["Patch", "Rotate keys"])

    message = format_alert(make_article(), draft, 8.666)

    for expected in ["GitLab flaw", "8.67", "CVE-2026-1234", "What happened", "Why", "- Patch", "- Rotate keys", "http://x/1"]:
        assert expected in message


def test_slack_error_does_not_leak_the_webhook_url(monkeypatch):
    def failing_post(*args, **kwargs):
        raise httpx.ConnectError("failed for https://hooks.slack.com/secret")

    monkeypatch.setattr(httpx, "post", failing_post)

    with pytest.raises(RuntimeError) as error:
        SlackNotifier("https://hooks.slack.com/secret").send("hello")

    assert "secret" not in str(error.value)
    assert error.value.__suppress_context__ is True


def test_slack_escapes_control_characters(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    SlackNotifier("https://hooks.slack.com/x").send("<a> & b")

    assert captured["text"] == "&lt;a&gt; &amp; b"
