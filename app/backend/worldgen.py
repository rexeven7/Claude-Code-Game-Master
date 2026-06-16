"""In-app world creation: import a book (PDF/TXT/DOCX/MD) or author a new world from a
brief, producing a playable KIT (ruleset.json with is_kit) that appears in the New
Adventure picker. Reuses the lib/ pipeline (text extraction, the normalization passes,
overview/voice seeding) and the app's swappable GM provider for the LLM steps. RAG
indexing is best-effort (only when sentence-transformers/torch are installed)."""
import os, sys, json, re, datetime, asyncio
import engine

if str(engine.REPO) not in sys.path:
    sys.path.insert(0, str(engine.REPO))      # so `import lib.X` and flat lib imports resolve


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def _emit(emit, **ev):
    if not emit:
        return
    r = emit(ev)
    if asyncio.iscoroutine(r):
        await r


def _strip_json(text):
    """Pull one JSON object out of a model response (handles ``` fences / prose)."""
    if not text:
        return {}
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", t, re.DOTALL)
    if m:
        t = m.group(1).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1 and j > i:
        t = t[i:j + 1]
    try:
        return json.loads(t)
    except Exception:
        return {}


def _windows(text, size=12000, max_windows=6):
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    return [text[i:i + size] for i in range(0, min(len(text), size * max_windows), size)]


_EXTRACT = {
    "npcs": ("npcs", "Extract every named or distinctive CHARACTER. For each give an 80+ word "
             "\"description\", an \"attitude\" (friendly|neutral|hostile|suspicious|helpful), "
             "\"location_tags\" [places], \"events\" [], \"dialogue\" [2-3 verbatim quotes if any], "
             "and \"stats\" {ac,hp,cr,abilities[]} ONLY if the text states them."),
    "locations": ("locations", "Extract every named PLACE, room, region, or scene. For each give a "
                  "\"position\", a rich \"description\", \"connections\" [{to,path}], \"features\"[], "
                  "\"inhabitants\"[], \"hazards\"[], and \"notes\"."),
    "items": ("items", "Extract magic items, treasure, and narratively significant OBJECTS. For each give "
              "\"description\", \"type\", \"rarity\", \"mechanics\", \"value\", \"location\", "
              "\"attunement\" (bool), \"cursed\" (bool)."),
    "plots": ("plot_hooks", "Extract quests, plot points, scenes, and themes. For each give \"description\", "
              "\"type\" (main|side|personal|world|optional), \"npcs\"[], \"locations\"[], "
              "\"objectives\"[], \"rewards\", \"consequences\", \"level_range\"."),
}


async def _extract_kind(provider, kind, text, emit):
    wrapper, instr = _EXTRACT[kind]
    sysp = ("You are a meticulous tabletop-RPG extraction agent. " + instr +
            f"\nReturn ONLY JSON shaped {{\"{wrapper}\": {{\"<Name>\": {{ ...fields... }}}}}} with no "
            f"commentary; key each entity by its name and include a \"name\" field. Found none -> "
            f"{{\"{wrapper}\": {{}}}}.")
    merged, wins = {}, _windows(text)
    for n, w in enumerate(wins):
        await _emit(emit, type="progress", step=f"extracting {kind} ({n + 1}/{len(wins)})")
        try:
            out = await provider.complete(sysp, w, max_tokens=4096, temperature=0.2)
        except Exception as e:
            await _emit(emit, type="progress", step=f"{kind} {n + 1} failed: {e}")
            continue
        data = _strip_json(out)
        inner = data.get(wrapper, data) if isinstance(data, dict) else {}
        if isinstance(inner, dict):
            for k, v in inner.items():
                if isinstance(v, dict):
                    v.setdefault("name", k)
                    merged[k] = v
    return merged


_DEFAULT_RULESET = {"name": "Imported World", "system": "d20", "stat_schema": {"attributes": [], "vitals": ["hp"]},
                    "progression": {"model": "milestone"}, "resolution": {"model": "d20-vs-dc"},
                    "active_agents": ["monster-manual", "rules-master", "gear-master", "loot-dropper", "npc-builder"],
                    "rules_doc": "rules.md"}


async def _author_ruleset(provider, name, text):
    sysp = ("You design a tabletop World Kit. Given source material, output ONLY JSON for ruleset.json with keys: "
            "name, system (e.g. 'd20' or 'Year Zero Engine'), resolution {model: 'd20-vs-dc' or 'yze-pool'}, "
            "stat_schema {attributes:[...], vitals:['hp' or attribute names]}, progression {model: 'milestone'|'xp-levels'}, "
            "active_agents:[...], rules_doc:'rules.md'. Pick the resolution model that best fits the source's genre "
            "(gritty/survival -> yze-pool; heroic fantasy -> d20-vs-dc).")
    try:
        data = _strip_json(await provider.complete(sysp, (text or "")[:8000], max_tokens=1500, temperature=0.4))
    except Exception:
        data = {}
    rs = dict(_DEFAULT_RULESET)
    if isinstance(data, dict):
        for k in ("name", "system", "resolution", "stat_schema", "progression", "active_agents"):
            if data.get(k):
                rs[k] = data[k]
    rs["name"] = rs.get("name") or name
    rs["rules_doc"] = "rules.md"
    return rs


async def _author_bible(provider, name, text):
    sysp = ("You distill a source into a world bible. Output ONLY JSON with keys: name, tone (short), "
            "themes:[...], voice:{style:'one sentence on the prose voice', sample_passages:[3 SHORT VERBATIM "
            "quotes copied exactly from the source], vocab:[distinctive words]}, "
            "factions:{nodes:[{name}],edges:[]}, geography:{nodes:[{name}],edges:[]}, signature_systems:[...].")
    try:
        data = _strip_json(await provider.complete(sysp, (text or "")[:9000], max_tokens=2000, temperature=0.5))
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    voice_in = data.get("voice") or {}
    try:
        from lib.book_bible import draft_voice
        voice = draft_voice(voice_in.get("style", ""), voice_in.get("sample_passages", []) or [],
                            text or "", voice_in.get("vocab", []) or [])
    except Exception:
        voice = {"style": voice_in.get("style", ""), "sample_passages": [], "vocab": []}
    bible = {
        "name": data.get("name") or name,
        "tone": data.get("tone", ""),
        "themes": data.get("themes", []) or [],
        "voice": voice,
        "factions": data.get("factions") or {"nodes": [], "edges": []},
        "geography": data.get("geography") or {"nodes": [], "edges": []},
        "signature_systems": data.get("signature_systems", []) or [],
        "confirmed": True,
    }
    return bible


_PASSES = [
    ("cap entities", "extraction_cap", "cap_campaign", {}),
    ("normalize connections", "connection_normalize", "run_normalize", {}),
    ("canonicalize refs", "integrity_gate", "run_gate", {"strict": False}),
    ("reconcile locations", "location_reconcile", "run_reconcile", {}),
    ("stub minor entities", "minor_stubs", "run_stubs", {}),
    ("stat NPCs", "npc_stats", "run_enrich", {}),
    ("build plot spine", "plot_spine", "apply_spine", {}),
]


async def _run_passes(dest, emit):
    """Run the deterministic normalization passes best-effort; never fatal."""
    import importlib
    for label, mod, fn, kw in _PASSES:
        await _emit(emit, type="progress", step=label)
        try:
            m = importlib.import_module(f"lib.{mod}")
            getattr(m, fn)(str(dest), **kw)
        except SystemExit:
            await _emit(emit, type="progress", step=f"{label}: skipped (gate)")
        except Exception as e:
            await _emit(emit, type="progress", step=f"{label}: skipped ({e})")


def _first_location(dest):
    locs = engine._load(dest / "locations.json") or {}
    for nm, v in locs.items():
        if isinstance(v, dict):
            return nm
    return "Starting Point"


def _finish_kit(slug, dest, display_name, ruleset, emit):
    """Write overview + seed opening; mark active; return slug."""
    from json_ops import atomic_write_json
    start = _first_location(dest)
    if start == "Starting Point" and not (engine._load(dest / "locations.json") or {}):
        atomic_write_json(dest / "locations.json",
                          {start: {"name": start, "description": "Where the story begins.",
                                   "discovered": _now(), "connections": []}})
    ov = {"campaign_name": display_name, "current_character": None, "session_count": 0,
          "genre": ruleset.get("system", ""), "time_of_day": "morning",
          "current_date": "Day 1", "campaign_rules": {},
          "player_position": {"current_location": start, "previous_location": None, "arrival_time": _now()}}
    atomic_write_json(dest / "campaign-overview.json", ov)
    for f, default in (("facts.json", {}), ("consequences.json", {"active": [], "resolved": []}),
                       ("plots.json", {}), ("npcs.json", {}), ("items.json", {})):
        if not (dest / f).exists():
            atomic_write_json(dest / f, default)
    (dest / "session-log.md").write_text(f"# {display_name}\n\nA new world, ready to explore.\n", encoding="utf-8")
    try:
        from lib.overview_seed import set_rules_doc
        set_rules_doc(str(dest))
    except Exception:
        pass
    try:
        from lib.opening_seed import seed_opening
        seed_opening(str(dest))
    except Exception:
        pass
    try:
        from campaign_manager import CampaignManager
        CampaignManager(str(engine.REPO / "world-state")).set_active(slug)
    except Exception:
        pass
    return slug


async def import_pdf(display_name, src_path, provider=None, emit=None):
    """Import a document into a new, playable kit."""
    import gm
    from json_ops import atomic_write_json
    provider = provider or gm._provider()
    slug = engine._slug(display_name) or engine._slug(os.path.splitext(os.path.basename(str(src_path)))[0]) or "imported-world"
    dest = engine.campaign_dir(slug)
    if dest.exists():
        raise ValueError(f"A world '{slug}' already exists.")
    dest.mkdir(parents=True)
    (dest / "images").mkdir(exist_ok=True)
    (dest / "saves").mkdir(exist_ok=True)

    await _emit(emit, type="progress", step="reading document")
    from lib.content_extractor import ContentExtractor
    text = ContentExtractor().extract_text(str(src_path)) or ""

    try:
        from lib.rag import check_rag_available
        if check_rag_available():
            await _emit(emit, type="progress", step="building search index")
            from lib.rag import RAGExtractor
            RAGExtractor(str(dest)).extract_from_document(str(src_path), clear_existing=True)
        else:
            await _emit(emit, type="progress", step="search index skipped (no RAG deps on this machine)")
    except Exception as e:
        await _emit(emit, type="progress", step=f"search index skipped ({e})")

    npcs = await _extract_kind(provider, "npcs", text, emit)
    locations = await _extract_kind(provider, "locations", text, emit)
    items = await _extract_kind(provider, "items", text, emit)
    plots = await _extract_kind(provider, "plots", text, emit)
    atomic_write_json(dest / "npcs.json", npcs)
    atomic_write_json(dest / "locations.json", locations)
    atomic_write_json(dest / "items.json", items)
    atomic_write_json(dest / "plots.json", plots)

    await _emit(emit, type="progress", step="authoring the rule kit")
    ruleset = await _author_ruleset(provider, display_name, text)
    ruleset["is_kit"] = True
    atomic_write_json(dest / "ruleset.json", ruleset)
    (dest / "rules.md").write_text(
        f"# {ruleset.get('name', display_name)} - World Kit\n\nSystem: {ruleset.get('system', '')} "
        f"({(ruleset.get('resolution') or {}).get('model', '')}). Imported into Mythwright.\n", encoding="utf-8")

    await _emit(emit, type="progress", step="distilling the world's voice")
    atomic_write_json(dest / "world-bible.json", await _author_bible(provider, display_name, text))

    await _run_passes(dest, emit)
    _finish_kit(slug, dest, display_name, ruleset, emit)
    await _emit(emit, type="done", kit=slug, name=display_name)
    return slug


async def new_game(spec, provider=None, emit=None):
    """Author an original world from a brief: {name, premise, tone, genre, magic, system?}."""
    import gm
    from json_ops import atomic_write_json
    provider = provider or gm._provider()
    name = (spec.get("name") or "New World").strip()
    slug = engine._slug(name) or "new-world"
    dest = engine.campaign_dir(slug)
    if dest.exists():
        raise ValueError(f"A world '{slug}' already exists.")
    dest.mkdir(parents=True)
    (dest / "images").mkdir(exist_ok=True)
    (dest / "saves").mkdir(exist_ok=True)

    brief = json.dumps({k: spec.get(k) for k in ("name", "premise", "tone", "genre", "magic", "system") if spec.get(k)})
    await _emit(emit, type="progress", step="dreaming up the world")
    sysp = ("You are a world designer. From the brief, invent a coherent setting and output ONLY JSON with keys: "
            "bible {name, tone, themes:[], voice:{style, sample_passages:[], vocab:[]}, factions:{nodes:[{name}],edges:[]}, "
            "geography:{nodes:[{name}],edges:[]}, signature_systems:[...]}, "
            "ruleset {name, system, resolution:{model}, stat_schema:{attributes:[],vitals:['hp']}, progression:{model}, active_agents:[], rules_doc:'rules.md'}, "
            "locations {<Name>:{position, description, connections:[{to,path}], features:[]}}, "
            "npcs {<Name>:{description, attitude, location_tags:[]}}, "
            "plots {<Name>:{description, type, objectives:[]}}, "
            "start_location '<a location name>'.")
    try:
        data = _strip_json(await provider.complete(sysp, brief, max_tokens=4000, temperature=0.8))
    except Exception:
        data = {}
    data = data if isinstance(data, dict) else {}

    bible_in = data.get("bible") or {}
    try:
        from lib.book_bible import draft_voice
        v = bible_in.get("voice") or {}
        bible_in["voice"] = draft_voice(v.get("style", ""), v.get("sample_passages", []) or [],
                                        spec.get("premise", "") or "", v.get("vocab", []) or [])
    except Exception:
        bible_in["voice"] = bible_in.get("voice") or {"style": "", "sample_passages": [], "vocab": []}
    bible = {"name": bible_in.get("name") or name, "tone": bible_in.get("tone", spec.get("tone", "")),
             "themes": bible_in.get("themes", []) or [], "voice": bible_in["voice"],
             "factions": bible_in.get("factions") or {"nodes": [], "edges": []},
             "geography": bible_in.get("geography") or {"nodes": [], "edges": []},
             "signature_systems": bible_in.get("signature_systems", []) or [], "confirmed": True}
    atomic_write_json(dest / "world-bible.json", bible)

    rs = dict(_DEFAULT_RULESET)
    rin = data.get("ruleset") or {}
    for k in ("name", "system", "resolution", "stat_schema", "progression", "active_agents"):
        if rin.get(k):
            rs[k] = rin[k]
    rs["name"] = rs.get("name") or name
    rs["rules_doc"] = "rules.md"
    rs["is_kit"] = True
    atomic_write_json(dest / "ruleset.json", rs)
    (dest / "rules.md").write_text(f"# {name} - World Kit\n\nSystem: {rs.get('system','')} "
                                   f"({(rs.get('resolution') or {}).get('model','')}).\n", encoding="utf-8")

    atomic_write_json(dest / "locations.json", data.get("locations") if isinstance(data.get("locations"), dict) else {})
    atomic_write_json(dest / "npcs.json", data.get("npcs") if isinstance(data.get("npcs"), dict) else {})
    atomic_write_json(dest / "plots.json", data.get("plots") if isinstance(data.get("plots"), dict) else {})

    await _run_passes(dest, emit)
    slug = _finish_kit(slug, dest, name, rs, emit)
    # honor an explicit start_location if the model named one
    start = data.get("start_location")
    if start and (engine._load(dest / "locations.json") or {}).get(start):
        ov = engine._load(dest / "campaign-overview.json") or {}
        ov.setdefault("player_position", {})["current_location"] = start
        atomic_write_json(dest / "campaign-overview.json", ov)
    await _emit(emit, type="done", kit=slug, name=name)
    return slug
