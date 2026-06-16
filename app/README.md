# Forbidden Lands — DM App

A local-first (web-ready) app over the **existing** Forbidden Lands engine. It does **not**
reimplement the rules — the FastAPI backend imports `lib/` and reads the same
`world-state/campaigns/*` JSON, so the app and your Claude Code sessions share campaigns.

## Run (two terminals)
```
# backend
cd app/backend && pip install -r requirements.txt   # or: uv pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# frontend
cd app/frontend && npm install && npm run dev        # http://localhost:5173 (proxies /api,/ws -> :8000)
```
Keys go in `app/backend/.env` (OPENAI_API_KEY for images; ANTHROPIC_API_KEY if GM_PROVIDER=claude).

## File map
- `backend/main.py` — FastAPI: REST (campaigns, character, gallery, image, dice, `/api/fbl/options`,
  `POST /api/campaigns` create, `POST /api/campaigns/{cid}/generate`) + WebSocket `/ws/{cid}`
  (play turns, `{dice:...}` steps, `{illustrate:true}`).
- `backend/engine.py` — bridge to `lib/` + world-state. Campaign list/detail, spoiler-safe gallery,
  **kit sharing** (`kit_ref` / `rag_dir` / `asset_path`), and **`create_fbl_campaign(name, spec)`**.
- `backend/gm.py` — GM loop: provider (Ollama/Claude), per-turn RAG, on-demand skill docs, tool
  routing through the REAL `lib/` managers, prose tool-call parser, **`dice_step`**
  (confirm -> roll/score -> push -> keep), **`illustrate_now`**, `run_turn`, `transcript`.
- `backend/fbl_create.py` + `fbl_creation.json` — PHB-grounded **character creation** data
  (kins, professions w/ real skills + 3 talents + Pride + Dark Secret + gear, 46 general talents,
  age rules). `options()` feeds the wizard; `build_from_spec()` assembles the sheet.
- `backend/fbl_generators.py` + `fbl_tables.json` — generator tools (legend / monster pick+build /
  NPC / site) that roll **real book tables** extracted from the PDFs; enriched by RAG on the user's machine.
- `backend/extract_fbl_tables.py` — one-time extractor (Book of Beasts roster + GM's Guide demon
  builder) -> `fbl_tables.json`. (`fbl_creation.json` was assembled the same way from the Player's Handbook.)
- `frontend/src/App.tsx` + `index.css` — Dashboard, **New Adventure wizard** (Identity / Attributes /
  Skills / Talents / Pride & Secret / Look / Review), play view (pinned scene image + independently
  scrolling transcript), drawer (Character/Party/Dice/Maps/Tools), **DiceWidget**, **ToolsPanel**.

## Key design decisions
- **New campaigns start at Hex I20**; Weatherstone is only a rumor (its site map stays hidden) until
  the party travels there and hears the legend.
- New campaigns **share the FBL "kit"** (~21MB RAG index + ~13MB site art) via a `kit_ref` pointer in
  `campaign-overview.json`; only small text/state files are copied, so each new game stays tiny.
- Set the active campaign with **`CampaignManager.set_active(name)`** — there is NO `.switch()` method
  (a wrong call silently no-ops and the GM then loads the PREVIOUS campaign's context).
- **RAG** (sentence-transformers + ChromaDB) only runs where torch is installed (the user's machine);
  the sandbox cannot query it. Structured tables are extracted from the user's own PDFs into
  `fbl_creation.json` / `fbl_tables.json` (real book data); RAG is for in-play grounding/narration.

## Providers
- GM: Ollama default (`GM_PROVIDER=ollama`, `GM_OLLAMA_MODEL`, e.g. qwen2.5:7b) or Claude
  (`GM_PROVIDER=claude`, `ANTHROPIC_API_KEY`). Readiness: `GET /api/gm/health`.
- Images: `OPENAI_API_KEY` (gpt-image).

## Dice
Both modes pause on a confirm widget showing the pool composition. Auto = the app rolls; Manual = you
enter the faces of your physical dice. Per-die symbols (6 = success, 1 = bane), Push reroll, then Keep
-> the GM narrates the outcome.

## Status
- [x] Play loop end-to-end (provider + tools over lib, streaming, persist-before-narrate)
- [x] PHB-grounded character creation wizard (attributes/skills/talents/Pride/Dark Secret/look)
- [x] New-campaign creator (Hex I20 start, kit sharing)
- [x] Tools/generators (real book tables) + on-demand image gen + per-die dice UX
- [ ] Real-time multiplayer (claim a PC, turn order) — next
- [ ] Optional: generators auto-persist into world-state; packaging (Tauri / web deploy + auth)

## Working on this code (IMPORTANT — this environment)
The Edit/Write file tools corrupt files that contain non-ASCII (em-dash, ellipsis, curly quotes,
emoji) on this Windows setup — truncation or UTF-16-style NULL bytes. For such files (most `.py`
here, `App.tsx`, `index.css`), WRITE VIA bash/Python with explicit `encoding="utf-8"` (heredoc or
read/replace/write); keep `Edit` to ASCII-only changes. After writing, verify: 0 null bytes +
`python -c "import ast; ast.parse(open(f).read())"` and `npx tsc --noEmit`.
