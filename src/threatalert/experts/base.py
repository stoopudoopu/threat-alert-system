from threatalert.llm import LLMClient
from threatalert.models import Article, ClientProfile, Score


class Expert:
    name: str
    system_prompt: str
    uses_client: bool = False

    def build_prompt(self, article: Article, client: ClientProfile) -> str:
        cves = ", ".join(article.cves) or "none found"
        prompt = f"""<article>
<title>{article.title}</title>
<summary>{article.summary}</summary>
<cves>{cves}</cves>
</article>"""
        if self.uses_client:
            stack = ", ".join(client.tech_stack)
            prompt = f"""<company>
<tech_stack>{stack}</tech_stack>
<description>{client.description}</description>
</company>

{prompt}"""
        return prompt

    def score(self, article: Article, client: ClientProfile, llm: LLMClient) -> Score:
        return llm.parse("scoring", self.system_prompt, self.build_prompt(article, client), Score)
