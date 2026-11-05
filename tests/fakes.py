class FakeLLM:
    """Returns a fixed answer and records what it receives, with no network or cost."""

    def __init__(self, response=None):
        self.response = response
        self.calls = []

    def parse(self, role, system, prompt, schema):
        self.calls.append({"role": role, "system": system, "prompt": prompt, "schema": schema})
        return self.response
