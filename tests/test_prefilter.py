from threatalert.prefilter import extract_cves
from threatalert.models import Article, ClientProfile, DeepRelevance, Relevance
from threatalert.prefilter import deep_relevance, extract_cves, quick_relevance


def test_finds_a_cve():
    assert extract_cves("Flaw CVE-2026-58882 in Android") == ["CVE-2026-58882"]


def test_lowercase_is_normalized():
    assert extract_cves("flaw cve-2026-1234") == ["CVE-2026-1234"]


def test_repeated_cve_appears_once():
    assert extract_cves("CVE-2026-1234 and again CVE-2026-1234") == ["CVE-2026-1234"]

def test_cve_mentioned_not_a_report():
    assert extract_cves("Something about a cve") == []


def test_two_cves_mentioned():
    assert extract_cves("cve-2025-1234 and cve-2026-1111") == ["CVE-2025-1234", "CVE-2026-1111"]

class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, role, system, prompt, schema):
        self.calls.append({"role": role, "prompt": prompt})
        return self.response


def test_quick_relevance_sends_only_stack_and_article():
    article = Article(id="1", source="test", title="GitLab flaw", link="http://x", summary="A bug", published=None)
    client = ClientProfile(name="Acme", tech_stack=["GitLab", "Azure AD"], description="Long description")
    llm = FakeLLM(Relevance(reasoning="Uses GitLab", verdict="yes"))

    result = quick_relevance(article, client, llm)

    assert result.verdict == "yes"
    assert llm.calls[0]["role"] == "scoring"
    assert "GitLab, Azure AD" in llm.calls[0]["prompt"]
    assert "GitLab flaw" in llm.calls[0]["prompt"]
    assert "Long description" not in llm.calls[0]["prompt"]

def test_deep_relevance_sends_description_and_clean_content():
    article = Article(id="1", source="test", title="Flaw", link="http://x", summary="Short",
                      content="<p>Full <b>text</b></p>", published=None)
    client = ClientProfile(name="Acme", tech_stack=["GitLab"], description="Long description")
    llm = FakeLLM(DeepRelevance(reasoning="Affected", verdict="yes"))

    deep_relevance(article, client, llm)

    assert llm.calls[0]["role"] == "deep_relevance"
    assert "Long description" in llm.calls[0]["prompt"]
    assert "Full text" in llm.calls[0]["prompt"]
    assert "<p>" not in llm.calls[0]["prompt"]


def test_deep_relevance_falls_back_to_summary():
    article = Article(id="1", source="test", title="Flaw", link="http://x", summary="Short summary", published=None)
    client = ClientProfile(name="Acme", tech_stack=["GitLab"], description="Long description")
    llm = FakeLLM(DeepRelevance(reasoning="Unrelated", verdict="no"))

    deep_relevance(article, client, llm)

    assert "Short summary" in llm.calls[0]["prompt"]