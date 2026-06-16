"""GM agent loop, aiming at Claude-Code parity:
- Context = the harness's get_full_context (rules/voice/threads/NPC voices/clocks/consequences)
  + per-turn RAG from the books + on-demand skill rules + the full PC sheet.
- Tools route through the REAL managers so the living world reacts (consequence ticks on move,
  HP/gold/xp/inventory via player_manager).
- A specialist `lookup` tool (RAG) stands in for the book-first specialist agents.
- A text tool-call parser executes tools that a weak local model writes as PROSE (and strips them)."""
import os, sys, json, re, datetime, asyncio
import engine
sys.path.insert(0, str(engine.LIB))
if str(engine.REPO) not in sys.path:
    sys.path.insert(0, str(engine.REPO))
import dice
from json_ops import atomic_write_json

ROOMS: dict[str, list] = {}
ROOM_MODE: dict[str, str] = {}
PENDING: dict[str, dict] = {}
ROOM_CTX: dict[str, tuple] = {}     # cid -> (passages, skill, skill_doc)

# ---------- provider ----------
def _provider():
    if os.environ.get("GM_PROVIDER", "ollama").lower() == "claude":
        from llm.claude import ClaudeProvider; return ClaudeProvider()
    from llm.ollama import OllamaProvider; return OllamaProvider()

# ---------- RAG (every beat) ----------
def _retrieve(cid, query, k=4):
    try:
        from lib.rag.rag_extractor import RAGExtractor
        rx = RAGExtractor(str(engine.rag_dir(cid)))   # shared kit index when the campaign has none
        if rx.vector_store.count() <= 0:
            return []
        return [(h.get("text") or "").strip().replace("\n", " ")[:450] for h in rx.query(query, n_results=k) if h.get("text")]
    except Exception:
        return []

# ---------- kit detection ----------
def _kit(cid):
    """Active rules kit: 'fbl' (Year Zero Engine) or 'dnd' (default d20)."""
    rs = engine._load(engine.campaign_dir(cid) / "ruleset.json")
    if not rs:
        kd = engine.kit_dir(cid)
        rs = engine._load(kd / "ruleset.json") if kd else None
    rs = rs or {}
    blob = json.dumps(rs).lower()
    if ("year zero" in blob or "forbidden lands" in blob
            or rs.get("resolution", {}).get("model") == "yze-pool"):
        return "fbl"
    return "dnd"

# ---------- on-demand skill rules (KIT-AWARE) ----------
_SKILL_KEYS = [
    (("level up", "level-up", "spend xp", "spend my xp", "raise my", "improve a skill", "train up", "buy a talent", "new talent", "advance my"), "gm-levelup"),
    (("attack", "fight", "hit", "strike", "stab", "shoot", "swing", "kill", "slay", "melee", "parry", "dodge", "wound", "ambush", "duel", "charge", "grapple"), "gm-combat"),
    (("talk", "persuade", "convince", "lie", "intimidate", "charm", "negotiate", "bargain", "threaten", "manipulate", "haggle"), "gm-social"),
    (("cast", "spell", "magic", "sorcery", "ritual", "rune", "willpower", "power word"), "gm-spellcasting"),
    (("travel", "journey", "hike", "march", "set out", "head for", "head to", "ride to", "make camp", "forage", "fish", "quarter day", "pathfinder", "lead the way", "hex", "wilderness"), "gm-travel"),
    (("cave", "ruin", "dungeon", "crypt", "tunnel", "chamber", "vault", "explore", "door", "castle", "adventure site"), "gm-dungeon"),
    (("sneak", "climb", "search", "heal", "craft", "track", "hunt", "scout", "lore", "pick", "sleight", "swim", "jump", "survive", "insight"), "gm-skills"),
    (("hungry", "thirsty", "sleepy", "cold", "starv", "freez", "exhaust"), "gm-conditions"),
]
_skill_cache: dict[str, str] = {}

def _kit_section(doc, kit):
    """Return only the active kit's slice of a kit-aware SKILL.md: the shared
    preamble plus every '## ' section EXCEPT the other kit's. Agnostic skills
    (no kit headings) are returned whole."""
    if kit == "fbl":
        keep, drop = ("forbidden lands", "year zero"), ("d&d", "dnd", "d20")
    else:
        keep, drop = ("d&d", "dnd", "d20"), ("forbidden lands", "year zero")
    parts = re.split(r'(?m)^(##\s+.*)$', doc)
    if len(parts) < 3:
        return doc.strip()
    out = [parts[0]]
    for i in range(1, len(parts) - 1, 2):
        head, body = parts[i], parts[i + 1]
        hl = head.lower()
        if any(m in hl for m in drop) and not any(m in hl for m in keep):
            continue
        out.append(head + body)
    res = "".join(out).strip()
    return res or doc.strip()

def _skill_for(cid, action):
    a = (action or "").lower()
    kit = _kit(cid)
    for keys, skill in _SKILL_KEYS:
        if any(k in a for k in keys):
            ck = f"{skill}:{kit}"
            if ck not in _skill_cache:
                try:
                    raw = (engine.REPO / ".claude" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                    _skill_cache[ck] = _kit_section(raw, kit)[:6000]
                except Exception:
                    _skill_cache[ck] = ""
            return skill, _skill_cache[ck]
    return None, ""

# ---------- FBL structured tables (book-grounded specialist lookups) ----------
_TABLES_CACHE: dict[str, dict] = {}
def _tables():
    if "d" not in _TABLES_CACHE:
        base = os.path.dirname(os.path.abspath(__file__)); d = {}
        for fn in ("fbl_tables.json", "fbl_creation.json"):
            try:
                d.update(json.load(open(os.path.join(base, fn), encoding="utf-8")))
            except Exception:
                pass
        _TABLES_CACHE["d"] = d
    return _TABLES_CACHE["d"]

def _tables_lookup(cid, query):
    """Stand in for the monster-manual / gear-master agents: surface matching
    book-grounded entries (bestiary roster, playable kins) for the FBL kit."""
    if _kit(cid) != "fbl":
        return []
    q = (query or "").lower(); d = _tables(); hits = []
    try:
        for m in d.get("monster_roster", []):
            nm = (m.get("name") or "").lower()
            if nm and (nm in q or (len(nm) > 4 and nm.split(",")[0].strip() in q)):
                hits.append(f"BESTIARY: '{m.get('name')}' is in the Book of Beasts roster - stat it book-first (STR/AGI[+WITS/EMP], a D6 monster-attack table, an Armor Rating; monsters do not weaken when wounded, are immune to fear, and can only be dodged).")
        kins = d.get("kins") or {}
        for k in (kins.keys() if isinstance(kins, dict) else kins):
            if isinstance(k, str) and k.lower() in q:
                hits.append(f"KIN: {k} is a playable Forbidden Lands kin.")
    except Exception:
        pass
    return hits[:6]

# ---------- tools ----------
TOOLS = [
  {"type": "function", "function": {"name": "roll_dice", "description": "Resolve an uncertain action with a Year Zero dice pool. base = the governing ATTRIBUTE rating, skill = the SKILL level, gear = gear/weapon bonus. NAME it: attribute (STR/AGI/WITS/EMP) + skill_name. >=1 six = success.",
    "parameters": {"type": "object", "properties": {"base": {"type": "integer"}, "skill": {"type": "integer"}, "gear": {"type": "integer"}, "push": {"type": "boolean"}, "attribute": {"type": "string"}, "skill_name": {"type": "string"}}, "required": ["base"]}}},
  {"type": "function", "function": {"name": "update_character", "description": "Apply changes to the PC (negative = damage/cost): hp_delta, attribute+attribute_delta, willpower_delta, gold_delta, xp_delta, add_item, condition.",
    "parameters": {"type": "object", "properties": {"hp_delta": {"type": "integer"}, "attribute": {"type": "string"}, "attribute_delta": {"type": "integer"}, "willpower_delta": {"type": "integer"}, "gold_delta": {"type": "integer"}, "xp_delta": {"type": "integer"}, "add_item": {"type": "string"}, "condition": {"type": "string"}}}}},
  {"type": "function", "function": {"name": "record_event", "description": "Persist a short fact about what happened.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "category": {"type": "string"}}, "required": ["text"]}}},
  {"type": "function", "function": {"name": "move_to", "description": "Move the party to a location (fires consequences/clocks; reveals its map).",
    "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
  {"type": "function", "function": {"name": "illustrate", "description": "Paint a scene image at a striking beat. Concrete VISUAL description, no game text/UI.",
    "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}, "title": {"type": "string"}}, "required": ["prompt"]}}},
  {"type": "function", "function": {"name": "lookup", "description": "Search the source books (rules, bestiary, Raven's Purge, legends) for facts about a monster, item, NPC, place, or rule. Use before asserting lore you are unsure of.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]

def _system(cid, mode="auto", passages=None, skill_doc=""):
    ch = engine._load(engine.campaign_dir(cid) / "character.json") or {}
    cr = (engine._load(engine.campaign_dir(cid) / "campaign-overview.json") or {}).get("campaign_rules", {})
    kit = _kit(cid)
    if kit == "fbl":
        dice_line = ("When an action is uncertain, call roll_dice and STOP -- do NOT narrate the result. The player confirms and rolls in the app, then you narrate the outcome from the returned result (>=1 success works; 0 fails and worsens the situation). "
                     "Always NAME the roll: pass attribute (STR/AGI/WITS/EMP) and skill_name, with base = the attribute rating, skill = the skill level, gear = the gear bonus.")
        intro = ("You are the Game Master of a Forbidden Lands (Year Zero Engine) campaign. Narrate in a grim, mythic, sparse voice -- one vivid beat at a time, second person, then hand back to the player. "
                 "There is no HP and no AC: the four attributes (STR/AGI/WITS/EMP) ARE the health tracks (0 = Broken), you hit on a single 6, and damage = the weapon's rating + 1 per extra 6. Push a roll for more 6s at the cost of attribute/gear banes (and +1 Willpower per base-die 1).")
    else:
        dice_line = ("When an action is uncertain, call roll_dice and STOP -- do NOT narrate the result. Decide the DC, the player confirms and rolls in the app, then you narrate by margin (>= DC succeeds; below fails and complicates). "
                     "Always NAME the roll: pass attribute (STR/DEX/CON/INT/WIS/CHA) and skill_name; base = the d20, skill = the ability + proficiency modifier.")
        intro = ("You are the Game Master of a Dungeons & Dragons 5e campaign. Narrate vividly -- one beat at a time, second person, then hand back to the player. "
                 "Resolve uncertain actions with a d20 + modifier vs a DC; track HP and AC.")
    header = [
        intro,
        dice_line,
        "Use TOOLS to act: roll_dice, update_character, record_event, move_to, illustrate, lookup. Call them via the tool interface -- NEVER write tool names, function calls, or image announcements (no 'BEHOLD', no 'illustrate(...)') in your prose. Apply outcomes with the tools BEFORE narrating them.",
        "If unsure about a monster, item, NPC, place, or rule, call lookup first and ground your answer in the result -- do not guess.",
        f"GEAR -- the PC carries EXACTLY these, never invent others: {(ch.get('inventory') or []) + (ch.get('equipment') or [])}",
        f"TALENTS: {ch.get('features') or []} | pride: {ch.get('pride')} | dark secret: {ch.get('dark_secret')}",
        "GROUND TRUTH: gear/attributes/skills/talents are authoritative; never invent items. End each beat with up to 3 SHORT suggestions, each on its own line as '1.' '2.' '3.'.",
    ]
    try:
        from session_manager import SessionManager
        ctx = SessionManager(str(engine.REPO / "world-state")).get_full_context()
    except Exception:
        ctx = ""
    parts = ["\n".join(header), ctx]
    if skill_doc:
        parts.append("RELEVANT RULES:\n" + skill_doc)
    if passages:
        parts.append("SOURCE PASSAGES (ground narration AND rulings in these book excerpts; prefer them over guessing):\n- " + "\n- ".join(passages))
    return "\n\n".join(p for p in parts if p)

# ---------- text tool-call parser (for weak local models) ----------
_TOOL_RE = re.compile(r'\b(illustrate|roll_dice|move_to|update_character|record_event|lookup)\s*\(([^)]*)\)', re.IGNORECASE)
# Colon/dash form the local model loves: "Illustrate: a dark lab", "**Illustrate -** ...".
# Matches anywhere (line-start OR mid-line), captures the scene description to end of line.
_ILLUS_RE = re.compile(r'(?im)\*{0,2}\s*illustrate\b\s*[:\-—]\s*(.+?)\s*\*{0,2}\s*$')
_KV_DQ = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_KV_SQ = re.compile(r"(\w+)\s*=\s*'([^']*)'")
_KV_NUM = re.compile(r'(\w+)\s*=\s*(-?\d+)')
def _parse_text_tools(text):
    text = text or ""
    calls, spans = [], []
    for m in _TOOL_RE.finditer(text):
        args = {}
        for rx in (_KV_DQ, _KV_SQ):
            for k, v in rx.findall(m.group(2)): args[k] = v
        for k, v in _KV_NUM.findall(m.group(2)):
            args.setdefault(k, int(v))
        calls.append({"name": m.group(1).lower(), "args": args}); spans.append((m.start(), m.end()))
    # colon/dash illustrate -> a real image call (and remove the line so it never leaks)
    for m in _ILLUS_RE.finditer(text):
        desc = (m.group(1) or "").strip().strip("*").strip()
        if len(desc) >= 8:
            calls.append({"name": "illustrate", "args": {"prompt": desc}}); spans.append((m.start(), m.end()))
    cleaned = text
    for s, e in sorted(spans, reverse=True): cleaned = cleaned[:s] + cleaned[e:]
    # belt-and-braces: strip any leftover bare tool-name lines / stray "illustrate:" / BEHOLD
    cleaned = re.sub(r'(?im)^\s*\*{0,2}\s*(illustrate|roll_dice|move_to|update_character|record_event|lookup)\b.*$', '', cleaned)
    cleaned = re.sub(r'(?im)\*{0,2}\s*illustrate\b\s*[:\-—]\s*.+?$', '', cleaned)
    cleaned = re.sub(r'(?im)^\s*BEHOLD[^\n]*$', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned, calls

# ---------- tool execution (routes through the REAL managers) ----------
def _exec(cid, name, args):
    cdir = engine.campaign_dir(cid); ws = str(engine.REPO / "world-state")
    try:
        if name == "roll_dice":
            st = dice.roll_pool(base=int(args.get("base", 0)), skill=int(args.get("skill", 0)), gear=int(args.get("gear", 0)))
            if args.get("push"): st = dice.push_pool(st)
            return {"successes": st["successes"], "success": st["success"], "pushed": st["pushed"], "attribute_banes": st["attribute_banes"], "willpower_gained": st["willpower"]}
        if name == "move_to":
            from session_manager import SessionManager
            from consequence_manager import ConsequenceManager
            SessionManager(ws).move_party(args["location"])
            fired = ConsequenceManager(ws).tick_from_session(limit=2) or []
            return {"ok": True, "location": args["location"], "consequences": [c.get("consequence") for c in fired]}
        if name == "update_character":
            from player_manager import PlayerManager
            pm = PlayerManager(ws); nm = (engine._load(cdir / "character.json") or {}).get("name") or "PC"
            if "hp_delta" in args: pm.modify_hp(nm, int(args["hp_delta"]))
            if "gold_delta" in args: pm.modify_gold(nm, int(args["gold_delta"]))
            if "xp_delta" in args: pm.award_xp(nm, int(args["xp_delta"]))
            if args.get("add_item"): pm.modify_inventory(nm, "add", args["add_item"])
            if args.get("condition"): pm.modify_condition(nm, "add", args["condition"])
            if args.get("attribute") or "willpower_delta" in args:   # FBL-specific: direct atomic
                ch = engine._load(cdir / "character.json") or {}
                if args.get("attribute"):
                    ca = ch.setdefault("current_attributes", dict(ch.get("attributes", {}))); k = str(args["attribute"]).lower()
                    if k in ca: ca[k] = max(0, ca[k] + int(args.get("attribute_delta", 0)))
                if "willpower_delta" in args and isinstance(ch.get("willpower"), dict):
                    w = ch["willpower"]; w["current"] = max(0, min(w.get("max", 10), w.get("current", 0) + int(args["willpower_delta"])))
                atomic_write_json(cdir / "character.json", ch)
            return {"ok": True}
        if name == "record_event":
            from note_manager import NoteManager
            try: NoteManager(ws).add_note(args["text"], args.get("category", "session_events"))
            except Exception:
                f = engine._load(cdir / "facts.json") or {}; f.setdefault(args.get("category", "session_events"), []).append(args["text"]); atomic_write_json(cdir / "facts.json", f)
            return {"ok": True}
        if name == "lookup":
            q = args.get("query", "")
            return {"passages": _retrieve(cid, q, 6) + _tables_lookup(cid, q)}
        if name == "illustrate":
            ch = engine._load(cdir / "character.json") or {}
            try:
                import image_gen as _ig
            except Exception as e:
                return {"error": f"image gen unavailable: {e}"}
            # image_gen resolves the campaign via a cwd-relative "world-state"; the backend runs
            # from app/backend, so force it to THIS campaign dir (absolute) regardless of cwd.
            _ig.resolve_campaign_dir = lambda *a, **k: cdir
            p, t = args.get("prompt", ""), args.get("title", "scene")
            nm = ch.get("name")
            chars = [nm] if nm else None      # signature is characters=[...]; injects the PC's locked look
            try:
                r = _ig.generate_image(prompt=p, title=t, characters=chars)
            except Exception as e:
                return {"error": str(e)}
            return {"ok": True, "file": r.get("rel_path") or r.get("path"), "path": r.get("path")}
    except Exception as e:
        return {"error": str(e)}
    return {"error": f"unknown tool {name}"}

# ---------- the loop ----------
async def _loop(cid, emit, provider, mode, passages=None, skill_doc=""):
    hist = ROOMS[cid]; system = _system(cid, mode, passages, skill_doc)
    for _ in range(6):
        raw = ""; native = []
        async for ev in provider.narrate(system, hist, TOOLS):
            if ev.get("type") == "text" and ev.get("text"):
                raw += ev["text"]; await emit({"type": "token", "text": ev["text"]})
            elif ev.get("type") == "tool_use":
                native.append(ev)
        cleaned, parsed = _parse_text_tools(raw)
        if raw:
            await emit({"type": "clean", "text": cleaned})          # replace streamed bubble w/ tool-syntax stripped
        calls = native + parsed
        if not calls:
            hist.append({"role": "assistant", "content": cleaned}); break
        hist.append({"role": "assistant", "content": cleaned,
                     "tool_calls": [{"function": {"name": c["name"], "arguments": c.get("args", {})}} for c in calls]})
        deferred = None
        for c in calls:
            if c["name"] == "roll_dice" and deferred is None:
                deferred = c; continue
            if c["name"] == "illustrate":                      # slow OpenAI call: keep the loop responsive
                await emit({"type": "status", "text": "painting a scene…"})
                res = await asyncio.to_thread(_exec, cid, c["name"], c.get("args", {}))
            else:
                res = _exec(cid, c["name"], c.get("args", {}))
            await emit({"type": "tool", "name": c["name"], "args": c.get("args", {}), "result": res})
            hist.append({"role": "tool", "name": c["name"], "content": json.dumps(res)})
        if deferred is not None:
            a = deferred.get("args", {})
            pool = {"base": int(a.get("base", 0)), "skill": int(a.get("skill", 0)), "gear": int(a.get("gear", 0)), "push": bool(a.get("push", False))}
            label = a.get("skill_name") or a.get("reason") or ""
            attribute = a.get("attribute", "")
            PENDING[cid] = {"call": deferred, "pool": pool, "state": None, "label": label, "attribute": attribute, "cid": cid}
            await emit({"type": "roll_request", "pool": pool, "mode": mode, "label": label, "attribute": attribute})
            return
    await emit({"type": "done"})

async def run_turn(cid, character, action, emit, provider=None, dice_mode="auto"):
    try:
        from campaign_manager import CampaignManager
        CampaignManager(str(engine.REPO / "world-state")).set_active(cid)
    except Exception:
        pass
    ROOM_MODE[cid] = dice_mode
    ROOMS.setdefault(cid, []).append({"role": "user", "content": f"[{character}] {action}"})
    loc = ((engine._load(engine.campaign_dir(cid) / "campaign-overview.json") or {}).get("player_position") or {}).get("current_location") or ""
    skill, skill_doc = _skill_for(cid, action)
    passages = _retrieve(cid, f"{action} {loc}")
    ROOM_CTX[cid] = (passages, skill, skill_doc)
    if passages: await emit({"type": "rag", "count": len(passages)})
    try:
        await _loop(cid, emit, provider or _provider(), dice_mode, passages, skill_doc)
    except Exception as e:
        await emit({"type": "error", "text": f"GM error: {e}"}); await emit({"type": "done"})

def _faces(st):
    return {"base": st.get("base", []), "skill": st.get("skill", []), "gear": st.get("gear", [])}

def _roll_state_payload(st, pend):
    return {"type": "roll_state", "faces": _faces(st),
            "successes": st["successes"], "success": st["success"], "pushed": st["pushed"],
            "can_push": st.get("can_push", False), "attribute_banes": st.get("attribute_banes", 0),
            "gear_banes": st.get("gear_banes", 0), "willpower": st.get("willpower", 0),
            "label": pend.get("label", ""), "attribute": pend.get("attribute", ""), "pool": pend.get("pool", {})}

async def dice_step(cid, payload, emit, provider=None):
    """Multi-step dice interaction: confirm -> roll/score -> (push) -> keep. Both dice
    modes pause here so the pool is shown, confirmed, and rolled with per-die symbols."""
    pend = PENDING.get(cid)
    if not pend:
        return
    try:
        from campaign_manager import CampaignManager
        CampaignManager(str(engine.REPO / "world-state")).set_active(cid)
    except Exception:
        pass
    pool = pend.get("pool", {})
    step = (payload.get("dice") or "").lower()
    if step == "roll":                                   # AUTO: the app rolls the pool
        pend["state"] = dice.roll_pool(base=pool.get("base", 0), skill=pool.get("skill", 0), gear=pool.get("gear", 0))
        await emit(_roll_state_payload(pend["state"], pend)); return
    if step == "score":                                  # MANUAL: player typed the physical faces
        pend["state"] = dice.score_faces(base=payload.get("base", []), skill=payload.get("skill", []),
                                         gear=payload.get("gear", []), pushed=bool(payload.get("pushed", False)))
        await emit(_roll_state_payload(pend["state"], pend)); return
    if step == "push":                                   # AUTO reroll of non-6/non-1
        st = pend.get("state")
        if st and not st.get("pushed"):
            pend["state"] = dice.push_pool(st)
        if pend.get("state"):
            await emit(_roll_state_payload(pend["state"], pend))
        return
    if step == "keep":                                   # finalize -> GM narrates the outcome
        st = pend.get("state") or dice.roll_pool(base=pool.get("base", 0), skill=pool.get("skill", 0), gear=pool.get("gear", 0))
        PENDING.pop(cid, None)
        result = {"successes": st["successes"], "success": st["success"], "pushed": st["pushed"],
                  "attribute_banes": st.get("attribute_banes", 0), "gear_banes": st.get("gear_banes", 0),
                  "willpower_gained": st.get("willpower", 0)}
        await emit({"type": "tool", "name": "roll_dice", "args": pend["call"].get("args", {}),
                    "result": {**result, "faces": _faces(st)}})
        ROOMS[cid].append({"role": "tool", "name": "roll_dice", "content": json.dumps(result)})
        passages, skill, skill_doc = ROOM_CTX.get(cid, ([], None, ""))
        try:
            await _loop(cid, emit, provider or _provider(), ROOM_MODE.get(cid, "auto"), passages, skill_doc)
        except Exception as e:
            await emit({"type": "error", "text": f"GM error: {e}"}); await emit({"type": "done"})


async def illustrate_now(cid, emit, hint=""):
    """On-demand illustration the player triggers from the UI: paints the CURRENT scene
    (last GM narration, or a location establishing shot) with the PC on-model, off the
    event loop so the UI stays responsive."""
    try:
        from campaign_manager import CampaignManager
        CampaignManager(str(engine.REPO / "world-state")).set_active(cid)
    except Exception:
        pass
    scene = (hint or "").strip()
    if not scene:
        for m in reversed(ROOMS.get(cid, [])):
            if m.get("role") == "assistant" and (m.get("content") or "").strip():
                scene = m["content"]; break
    scene = re.sub(r'(?im)^\s*\*{0,2}\s*\d+[.)].*$', '', scene or "").strip()
    ov = engine._load(engine.campaign_dir(cid) / "campaign-overview.json") or {}
    loc = (ov.get("player_position") or {}).get("current_location") or "the Forbidden Lands"
    if len(scene) < 8:
        scene = f"A moody, cinematic establishing shot of {loc} in the Forbidden Lands - grim mythic fantasy."
    await emit({"type": "status", "text": "painting a scene..."})
    res = await asyncio.to_thread(_exec, cid, "illustrate", {"prompt": scene[:1200], "title": loc})
    await emit({"type": "tool", "name": "illustrate", "args": {}, "result": res})
    await emit({"type": "done"})


def transcript(cid):
    out = []
    for m in ROOMS.get(cid, []):
        r = m.get("role")
        if r == "user": out.append({"role": "player", "text": m.get("content", "")})
        elif r == "assistant" and m.get("content"): out.append({"role": "gm", "text": m["content"], "done": True})
        elif r == "tool":
            try: res = json.loads(m.get("content", "{}"))
            except Exception: res = {}
            out.append({"role": "tool", "name": m.get("name"), "result": res})
    return out
