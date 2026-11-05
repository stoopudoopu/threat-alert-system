from abc import ABC, abstractmethod

import httpx


class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> None:
        ...


class ConsoleNotifier(Notifier):
    def send(self, message: str) -> None:
        print(message)


class SlackNotifier(Notifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str) -> None:
        # Slack treats these three characters as control characters.
        text = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        try:
            response = httpx.post(self.webhook_url, json={"text": text}, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as error:
            # The webhook URL is a secret, and httpx includes it in its error messages.
            raise RuntimeError(f"Slack delivery failed: {type(error).__name__}") from None
