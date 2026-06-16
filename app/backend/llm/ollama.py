"""Free/local GM provider via Ollama (a separate app, NOT a pip package).
Install it from https://ollama.com/download, then: ollama pull gemma4
This client only needs httpx; it talks to the Ollama server over HTTP."""
import os, json, httpx
from .base import GMProvider

class OllamaProvider(GMProvider):
    name = "ollama"
    MODEL = os.environ.get("GM_OLLAMA_MODEL", "gemma4")
    HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    async def narrate(self, system, messages, tools=None):
        payload = {"model": self.MODEL, "stream": True,
                   "messages": [{"role": "system", "content": system}] + messages,
                   "options": {"temperature": float(os.environ.get("GM_TEMPERATURE", "0.7"))}}
        if tools:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=None) as c:
                async with c.stream("POST", f"{self.HOST}/api/chat", json=payload) as r:
                    if r.status_code != 200:
                        body = (await r.aread()).decode("utf-8", "ignore")[:300]
                        yield {"type": "text", "text":
                               f"[Ollama returned {r.status_code}. Is the model pulled?  ollama pull {self.MODEL}\n{body}]"}
                        yield {"type": "done"}; return
                    async for line in r.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except Exception:
                            continue
                        msg = chunk.get("message", {}) or {}
                        if msg.get("content"):
                            yield {"type": "text", "text": msg["content"]}
                        for tc in (msg.get("tool_calls") or []):
                            fn = tc.get("function", {}) or {}
                            args = fn.get("arguments", {})
                            if isinstance(args, str):
                                try: args = json.loads(args)
                                except Exception: args = {}
                            yield {"type": "tool_use", "name": fn.get("name"), "args": args}
                        if chunk.get("done"):
                            yield {"type": "done"}; return
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as e:
            yield {"type": "text", "text":
                   f"[Can't reach Ollama at {self.HOST}. Install it from ollama.com, make sure it's running, "
                   f"then `ollama pull {self.MODEL}`.]"}
            yield {"type": "done"}; return
