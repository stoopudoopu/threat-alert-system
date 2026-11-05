import pytest
from fakes import FakeLLM
from pydantic import ValidationError

from threatalert.experts.exposure import ExposureExpert
from threatalert.experts.severity import SeverityExpert
from threatalert.experts.urgency import UrgencyExpert
from threatalert.models import Article, ClientProfile, Score


def make_article():
    return Article(id="1", source="test", title="RCE in GitLab", link="http://x",
                   summary="A critical bug", published=None, cves=["CVE-2026-1234"])


def make_client():
    return ClientProfile(name="Acme", tech_stack=["GitLab"], description="Secret client description")


def test_severity_expert_returns_score_from_llm():
    llm = FakeLLM(Score(reasoning="Critical", score=9))

    result = SeverityExpert().score(make_article(), make_client(), llm)

    assert result.score == 9
    assert llm.calls[0]["role"] == "scoring"
    assert llm.calls[0]["schema"] is Score


def test_severity_prompt_has_article_but_no_client_data():
    llm = FakeLLM(Score(reasoning="Critical", score=9))

    SeverityExpert().score(make_article(), make_client(), llm)

    assert "RCE in GitLab" in llm.calls[0]["prompt"]
    assert "CVE-2026-1234" in llm.calls[0]["prompt"]
    assert "Secret client description" not in llm.calls[0]["prompt"]


def test_score_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        Score(reasoning="Too high", score=11)


def test_urgency_prompt_has_article_but_no_client_data():
    llm = FakeLLM(Score(reasoning="Active", score=8))

    UrgencyExpert().score(make_article(), make_client(), llm)

    assert "RCE in GitLab" in llm.calls[0]["prompt"]
    assert "Secret client description" not in llm.calls[0]["prompt"]


def test_exposure_prompt_has_article_and_client_data():
    llm = FakeLLM(Score(reasoning="Exposed", score=9))

    ExposureExpert().score(make_article(), make_client(), llm)

    assert "RCE in GitLab" in llm.calls[0]["prompt"]
    assert "Secret client description" in llm.calls[0]["prompt"]
    assert "GitLab" in llm.calls[0]["prompt"]
