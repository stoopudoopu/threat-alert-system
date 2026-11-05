import anthropic
from pydantic import BaseModel


class LLMOutputError(Exception):
    """The model answered, but with a refusal or without usable output."""


class LLMClient:
    def __init__(self, models: dict[str, str]):
        self.client = anthropic.Anthropic()
        self.models = models

    def parse(self, role: str, system: str, prompt: str, schema: type[BaseModel]) -> BaseModel:
        response = self.client.messages.parse(
            model=self.models[role],
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        if response.stop_reason == "refusal":
            raise LLMOutputError(f"Model refused with role '{role}'")
        if response.parsed_output is None:
            raise LLMOutputError(f"No parsed output, stop_reason={response.stop_reason}")
        return response.parsed_output
