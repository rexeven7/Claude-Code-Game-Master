"""GM provider interface: the LLM brain behind a swappable interface so the app can
run on Claude (Anthropic API key) or a free local model (Ollama), chosen per campaign."""
from typing import AsyncIterator, List, Dict, Any

class GMProvider:
    name = "base"
    async def narrate(self, system: str, messages: List[Dict[str, Any]],
                      tools: List[Dict[str, Any]] | None = None) -> AsyncIterator[Dict[str, Any]]:
        """Yield events: {'type':'text','text':...} | {'type':'tool_use',...} | {'type':'done'}.
        Implemented by ClaudeProvider (Anthropic API) and OllamaProvider (local)."""
        raise NotImplementedError
        yield  # pragma: no cover
