from fakes import FakeLLM

from threatalert.models import Article, ClientProfile, DeepRelevance, Relevance
from threatalert.prefilter import deep_relevance, is_relevant, quick_relevance


def make_client():
    return ClientProfile(name="Acme", tech_stack=["GitLab", "Azure AD"], description="Long description")


def make_article(**fields):
    defaults = {"id": "1", "source": "test", "title": "GitLab flaw", "link": "http://x",
                "summary": "Short summary", "published": None}
    return Article(**(defaults | fields))


class SequenceLLM:
    """Returns its answers in order, one per call."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def parse(self, role, system, prompt, schema):
        self.calls += 1
        return self.responses.pop(0)


def test_quick_relevance_sends_only_stack_and_article():
    llm = FakeLLM(Relevance(reasoning="Uses GitLab", verdict="yes"))

    result = quick_relevance(make_article(), make_client(), llm)

    assert result.verdict == "yes"
    assert llm.calls[0]["role"] == "scoring"
    assert "GitLab, Azure AD" in llm.calls[0]["prompt"]
    assert "GitLab flaw" in llm.calls[0]["prompt"]
    assert "Long description" not in llm.calls[0]["prompt"]


def test_deep_relevance_sends_description_and_clean_content():
    llm = FakeLLM(DeepRelevance(reasoning="Affected", verdict="yes"))

    deep_relevance(make_article(content="<p>Full <b>text</b></p>"), make_client(), llm)

    assert llm.calls[0]["role"] == "deep_relevance"
    assert "Long description" in llm.calls[0]["prompt"]
    assert "Full text" in llm.calls[0]["prompt"]
    assert "<p>" not in llm.calls[0]["prompt"]


def test_deep_relevance_falls_back_to_summary():
    llm = FakeLLM(DeepRelevance(reasoning="Unrelated", verdict="no"))

    deep_relevance(make_article(), make_client(), llm)

    assert "Short summary" in llm.calls[0]["prompt"]


def test_quick_no_does_not_call_the_deep_filter():
    llm = SequenceLLM(Relevance(reasoning="Outside the stack", verdict="no"))

    assert is_relevant(make_article(), make_client(), llm) is False
    assert llm.calls == 1


def test_quick_yes_does_not_call_the_deep_filter():
    llm = SequenceLLM(Relevance(reasoning="In the stack", verdict="yes"))

    assert is_relevant(make_article(), make_client(), llm) is True
    assert llm.calls == 1


def test_unsure_is_decided_by_the_deep_filter():
    llm = SequenceLLM(
        Relevance(reasoning="Not clear", verdict="unsure"),
        DeepRelevance(reasoning="Unrelated", verdict="no"),
    )

    assert is_relevant(make_article(), make_client(), llm) is False
    assert llm.calls == 2
