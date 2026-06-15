# Forbidden Lands — DM App

A local-first (web-ready) app over the **existing** Forbidden Lands engine. It does **not**
reimplement the rules — the FastAPI backend imports `lib/` and reads the same
`world-state/campaigns/*` JSON, so the app and your Claude Code sessions share campaigns.

## Architecture
```
React (Vite + TS)  ⇄  FastAPI  ⇄  existing lib/ engine  +  world-state JSON
   Dashboard          REST + WebSocket    (dice, kit, RAG,    (per-campaign state)
   Play / Gallery                          managers, images)
        ▲
   GM brain = swappable PROVIDER:  Claude (Anthropic API key)  |  Ollama (free/local)
   Real-time multiplayer = WebSocket rooms (one per campaign)
```

## Run (two terminals)
```
# backend
cd app/backend && pip install -r requirements.txt   # or: uv pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# frontend
cd app/frontend && npm install && npm run dev        # http://localhost:5173 (proxies /api, /ws -> :8000)
```

## GM provider (the automated, no-dice GM)
- **Claude** — set `ANTHROPIC_API_KEY` (pay-per-token; ~cents/scene). Best narration + tool use.
- **Local/free** — run Ollama, set `GM_PROVIDER=ollama` (+ `GM_OLLAMA_MODEL`). Zero cost, lower quality.
- A subscription can't power a third-party app, so automated-Claude uses an API key.

## Dice modes
- **Auto** (server rolls): `GET /api/dice/yze?base=&skill=&gear=&push=`
- **Manual** (you roll real dice, enter faces): `POST /api/dice/score`  → scores 6s/banes/WP

## Status
- [x] Backend over the real engine — campaigns, character, threads, images, both dice modes (tested)
- [x] React Dashboard + campaign view + map/gallery + dice tray + live WebSocket panel
- [ ] GM agent loop — provider + small tool-loop over `lib/` managers, streaming over WS
- [ ] Play loop — scene → action → GM → persist → stream; auto/manual dice in context
- [ ] Multiplayer — claim a PC, turn order, broadcast to the room
- [ ] Tools/generators UI (monsters/items/legends/encounters) + on-demand image gen + new-campaign
- [ ] Packaging — web deploy + auth; desktop via Tauri

## Prerequisite for the local GM (Ollama)
Ollama is a **separate app**, not a Python package. Install it from https://ollama.com/download, then in a new terminal:
```
ollama pull qwen2.5:7b      # a tool-capable model
ollama list                 # verify
```
The backend talks to it at http://localhost:11434 (only needs httpx). Check readiness any time: GET http://localhost:8000/api/gm/health
