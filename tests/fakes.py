"""Fake OpenAI-compatible client for offline tests. No network, no API key."""
import types


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, **kw):
        self.calls.append(kw)
        if not self.replies:
            raise AssertionError("FakeClient ran out of replies")
        text = self.replies.pop(0)
        if isinstance(text, Exception):
            raise text
        msg = types.SimpleNamespace(content=text)
        choice = types.SimpleNamespace(message=msg, finish_reason="stop")
        usage = types.SimpleNamespace(prompt_tokens=100, completion_tokens=50)
        return types.SimpleNamespace(choices=[choice], usage=usage)
