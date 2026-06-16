"""Claude GM provider via the Anthropic Messages API (needs ANTHROPIC_API_KEY).
Implements complete() (one-shot, for world import/authoring) and narrate()
(non-streaming play turn with tool support). Anthropic uses content blocks +
tool_use/tool_result pairing, so the app's generic history is converted here."""
import os, json
from .base import GMProvider


class ClaudeProvider(GMProvider):
    name = "claude"
    MODEL = os.environ.get("GM_CLAUDE_MODEL", "claude-sonnet-4-6")

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")

    def _client(self):
        from anthropic import AsyncAnthropic         # imported lazily so the module loads without the dep
        return AsyncAnthropic(api_key=self.api_key)

    # ---- history / tool conversion (app's generic shape -> Anthropic blocks) ----
    def _to_anthropic(self, messages):
        out, pending_ids = [], []
        for m in messages:
            role = m.get("role")
            if role == "user":
                out.append({"role": "user", "content": [{"type": "text", "text": str(m.get("content") or "")}]})
            elif role == "assistant":
                blocks, ids = [], []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for i, tc in enumerate(m.get("tool_calls") or []):
                    fn = tc.get("function", {}) or {}
                    tid = tc.get("id") or f"tu_{len(out)}_{i}"
                    args = fn.get("arguments")
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except Exception: args = {}
                    blocks.append({"type": "tool_use", "id": tid, "name": fn.get("name"), "input": args or {}})
                    ids.append((tid, fn.get("name")))
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "..."}]})
                pending_ids = ids
            elif role == "tool":
                tid = None
                for j, (cid, cname) in enumerate(pending_ids):
                    if cname == m.get("name"):
                        tid = cid; pending_ids.pop(j); break
                if tid is None and pending_ids:
                    tid = pending_ids.pop(0)[0]
                tid = tid or f"tr_{len(out)}"
                block = {"type": "tool_result", "tool_use_id": tid, "content": str(m.get("content") or "")}
                if (out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list)
                        and out[-1]["content"] and out[-1]["content"][-1].get("type") == "tool_result"):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return out or [{"role": "user", "content": [{"type": "text", "text": "Begin."}]}]

    def _tools_to_anthropic(self, tools):
        conv = []
        for t in tools or []:
            fn = t.get("function", t) if isinstance(t, dict) else {}
            conv.append({"name": fn.get("name"), "description": fn.get("description", ""),
                         "input_schema": fn.get("parameters") or {"type": "object", "properties": {}}})
        return conv

    async def narrate(self, system, messages, tools=None):
        if not self.api_key:
            yield {"type": "text", "text": "[ANTHROPIC_API_KEY not set. Add it to app/backend/.env or use GM_PROVIDER=ollama.]"}
            yield {"type": "done"}; return
        kwargs = {"model": self.MODEL, "max_tokens": 1024, "system": system,
                  "messages": self._to_anthropic(messages)}
        if tools:
            kwargs["tools"] = self._tools_to_anthropic(tools)
        try:
            resp = await self._client().messages.create(**kwargs)
        except Exception as e:
            yield {"type": "text", "text": f"[Claude error: {e}]"}; yield {"type": "done"}; return
        for block in (resp.content or []):
            bt = getattr(block, "type", None)
            if bt == "text":
                yield {"type": "text", "text": block.text}
            elif bt == "tool_use":
                yield {"type": "tool_use", "name": block.name, "args": block.input or {}}
        yield {"type": "done"}

    async def complete(self, system, user, *, max_tokens=4096, temperature=0.3):
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        resp = await self._client().messages.create(
            model=self.MODEL, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user}])
        return "".join(getattr(b, "text", "") for b in (resp.content or []) if getattr(b, "type", None) == "text")
