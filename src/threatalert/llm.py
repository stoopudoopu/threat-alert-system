from abc import ABC, abstractmethod

import anthropic
from pydantic import BaseModel


class LLMRefusalError(Exception):
    pass


class LLM(ABC):
    @abstractmethod
    def parse(self, role: str, system: str, prompt: str, schema: type[BaseModel]) -> BaseModel:
        ...


class AnthropicLLM(LLM):
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
            raise LLMRefusalError(f"Model refused with role '{role}'")
        if response.parsed_output is None:
            raise ValueError(f"No parsed output, stop_reason={response.stop_reason}")
        return response.parsed_output