"""Claude GM provider via the Anthropic Messages API (pay-per-token, needs ANTHROPIC_API_KEY).
Streams narration + tool calls. Swap to the Agent SDK here if you prefer its machinery."""
import os
from .base import GMProvider

class ClaudeProvider(GMProvider):
    name = "claude"
    MODEL = os.environ.get("GM_CLAUDE_MODEL", "claude-sonnet-4-6")
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
    async def narrate(self, system, messages, tools=None):
        # TODO: stream from anthropic AsyncAnthropic with the gm tools; tool loop drives lib/ managers.
        raise NotImplementedError("ClaudeProvider.narrate: wire anthropic streaming + tool loop")
