"""Forbidden Lands DM - API backend. Wraps the existing engine (lib/) + world-state JSON.
REST for dashboard/tools/dice; WebSocket rooms for real-time multiplayer (GM loop wired next)."""
import sys
from pathlib import Path
from typing import List
import engine                                  # adds lib/ to sys.path
sys.path.insert(0, str(engine.LIB))
import dice                                    # the existing YZE dice engine
import gm                                      # the GM agent loop
import fbl_create                              # guided FBL character creation (the kit's inference)
import fbl_generators                          # legend/monster/NPC/site generator tools
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Forbidden Lands DM")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=False)

@app.get("/api/health")
def health():
    return {"ok": True, "repo": str(engine.REPO)}

import os as _os
import httpx as _httpx

@app.get("/api/gm/health")
def gm_health():
    provider = _os.environ.get("GM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        host = _os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model = _os.environ.get("GM_OLLAMA_MODEL", "qwen2.5:7b")
        try:
            r = _httpx.get(f"{host}/api/tags", timeout=2.0)
            names = [m.get("name", "") for m in r.json().get("models", [])]
            return {"provider": "ollama", "host": host, "reachable": True, "model": model,
                    "model_present": any(model.split(":")[0] in n for n in names), "models": names}
        except Exception as e:
            return {"provider": "ollama", "host": host, "reachable": False, "error": str(e),
                    "hint": f"Install Ollama from ollama.com, start it, then: ollama pull {model}"}
    if provider == "claude":
        return {"provider": "claude", "key_set": bool(_os.environ.get("ANTHROPIC_API_KEY"))}
    return {"provider": provider}

@app.get("/api/campaigns")
def campaigns():
    return engine.list_campaigns()

@app.get("/api/campaigns/{cid}")
def campaign(cid: str):
    d = engine.campaign_dir(cid)
    if not d.exists():
        raise HTTPException(404, "campaign not found")
    return engine.campaign_detail(cid)

@app.get("/api/campaigns/{cid}/images")
def images(cid: str):
    return {"images": engine.list_images(cid),
            "registry": engine._load(engine.campaign_dir(cid) / "site-images.json")}

@app.get("/api/campaigns/{cid}/gallery")
def gallery(cid: str):
    return engine.gallery(cid)

@app.get("/api/campaigns/{cid}/image")
def image_file(cid: str, path: str):
    if ".." in path:
        raise HTTPException(400, "bad path")
    base = engine.campaign_dir(cid).resolve()
    f = (base / path).resolve()
    if not f.is_file():
        f = engine.asset_path(cid, path).resolve()      # shared kit (site art) fallback
    kd = engine.kit_dir(cid)
    roots = [base] + ([kd.resolve()] if kd else [])
    if not any(r == f or r in f.parents for r in roots):
        raise HTTPException(400, "bad path")
    if not f.is_file():
        raise HTTPException(404, "image not found")
    return FileResponse(str(f))

# --- Character creation options + new-campaign creator (FBL kit, starts at Hex I20) ---
@app.get("/api/fbl/options")
def fbl_options():
    return fbl_create.options()

from typing import Dict, Any
class CreateBody(BaseModel):
    name: str
    character: Dict[str, Any] = {}

@app.post("/api/campaigns")
def create_campaign(body: CreateBody):
    try:
        cid = engine.create_fbl_campaign(body.name, body.character)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"id": cid, **engine.campaign_detail(cid)}

# --- Generator tools (legend / monster / npc / site) - real book tables + RAG ---
class GenBody(BaseModel):
    kind: str
    mode: str = "pick"
    named: bool = False

@app.post("/api/campaigns/{cid}/generate")
def generate(cid: str, body: GenBody):
    if not engine.campaign_dir(cid).exists():
        raise HTTPException(404, "campaign not found")
    return fbl_generators.generate(cid, body.kind, mode=body.mode, named=body.named)

# --- Dice: auto mode (server rolls) and manual mode (player enters faces) ---
@app.get("/api/dice/yze")
def dice_yze(base: int = 0, skill: int = 0, gear: int = 0, artifact: int = 0, push: bool = False):
    st = dice.roll_pool(base=base, skill=skill, gear=gear, artifact=[artifact] if artifact else None)
    if push:
        st = dice.push_pool(st)
    return dice._strip(st)

class Faces(BaseModel):
    base: List[int] = []
    skill: List[int] = []
    gear: List[int] = []
    negative: List[int] = []
    pushed: bool = False

@app.post("/api/dice/score")
def dice_score(f: Faces):
    return dice._strip(dice.score_faces(base=f.base, skill=f.skill, gear=f.gear,
                                        negative=f.negative, pushed=f.pushed))

# --- Real-time multiplayer rooms (foundation; turn-taking + GM agent loop next) ---
rooms: dict[str, set] = {}

@app.websocket("/ws/{cid}")
async def ws(websocket: WebSocket, cid: str):
    await websocket.accept()
    rooms.setdefault(cid, set()).add(websocket)

    async def broadcast(ev):
        for peer in list(rooms[cid]):
            try:
                await peer.send_json(ev)
            except Exception:
                rooms[cid].discard(peer)

    try:
        await websocket.send_json({"type": "connected", "campaign": cid, "players": len(rooms[cid])})
        await websocket.send_json({"type": "history", "entries": gm.transcript(cid)})
        while True:
            msg = await websocket.receive_json() or {}
            if msg.get("action"):
                character = msg.get("character") or "Player"
                await broadcast({"type": "action", "character": character, "text": msg["action"]})
                await gm.run_turn(cid, character, msg["action"], broadcast, dice_mode=msg.get("dice_mode", "auto"))
            elif msg.get("dice"):
                await gm.dice_step(cid, msg, broadcast)
            elif msg.get("illustrate"):
                await gm.illustrate_now(cid, broadcast, hint=msg.get("hint", ""))
    except WebSocketDisconnect:
        rooms[cid].discard(websocket)
