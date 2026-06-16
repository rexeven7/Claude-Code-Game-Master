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

    async def complete(self, system: str, user: str, *, max_tokens: int = 4096,
                       temperature: float = 0.3) -> str:
        """One-shot, non-streaming text completion (no tools) for world import/authoring.
        Default accumulates narrate() text; providers override for token/temperature control."""
        parts: List[str] = []
        async for ev in self.narrate(system, [{"role": "user", "content": user}], None):
            if ev.get("type") == "text" and ev.get("text"):
                parts.append(ev["text"])
        return "".join(parts)
