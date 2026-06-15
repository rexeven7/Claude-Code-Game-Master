"""Bridge to the existing Forbidden Lands engine (lib/) and world-state JSON.
The app reuses the proven Python engine rather than reimplementing the rules."""
import json, sys, shutil, datetime, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]      # .../Claude-Code-Game-Master
LIB = REPO / "lib"
CAMPAIGNS = REPO / "world-state" / "campaigns"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None

def list_campaigns():
    out = []
    if not CAMPAIGNS.exists():
        return out
    for d in sorted(CAMPAIGNS.iterdir()):
        ov = _load(d / "campaign-overview.json")
        if ov is None:
            continue
        out.append({
            "id": d.name,
            "name": ov.get("campaign_name", d.name),
            "genre": ov.get("genre"),
            "current_character": ov.get("current_character"),
            "session_count": ov.get("session_count", 0),
            "location": (ov.get("player_position") or {}).get("current_location"),
        })
    return out

def campaign_dir(cid):
    return CAMPAIGNS / cid

def campaign_detail(cid):
    d = campaign_dir(cid)
    ov = _load(d / "campaign-overview.json") or {}
    npcs = _load(d / "npcs.json") or {}
    party = {n: v for n, v in npcs.items() if v.get("is_party_member")}
    plots = _load(d / "plots.json") or {}
    return {
        "id": cid,
        "overview": ov,
        "character": _load(d / "character.json"),
        "party": party,
        "threads": [{"name": k, "type": v.get("type"), "status": v.get("status")} for k, v in plots.items()],
        "site_images": _load(d / "site-images.json"),
        "rules": ov.get("campaign_rules", {}),
    }

def list_images(cid):
    d = campaign_dir(cid) / "images"
    files = []
    if d.exists():
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                files.append(str(f.relative_to(campaign_dir(cid)).as_posix()))
    return files

def gallery(cid):
    """Spoiler-safe gallery: scene images generated during play + the world map + site maps
    ONLY for locations the party has actually been to (current/previous). Hides the official
    maps of sites they have not yet visited."""
    d = campaign_dir(cid)
    reg = _load(d / "site-images.json") or {}
    ov = _load(d / "campaign-overview.json") or {}
    pos = ov.get("player_position") or {}
    here = {(pos.get("current_location") or "").lower(), (pos.get("previous_location") or "").lower()}
    here.discard("")
    maps = []
    for site, rel in (reg.get("sites") or {}).items():
        base = site.split(" (")[0].lower()
        if any(base and (base in h or h in base) for h in here):
            maps.append({"label": site, "path": rel})
    if reg.get("world_map"):
        maps.append({"label": "World Map", "path": reg["world_map"]})
    scenes = []
    img_dir = d / "images"
    if img_dir.exists():
        for f in sorted(img_dir.glob("*.png")):
            scenes.append({"label": f.stem.replace("-", " ").strip(), "path": f"images/{f.name}"})
    return {"scenes": scenes, "maps": maps}

# ---------------------------------------------------------------- kit sharing
# New Forbidden Lands campaigns SHARE the big read-only assets of a template
# campaign (the 21MB RAG index + 13MB of site art) instead of copying them, via a
# `kit_ref` pointer in the overview. Small text files are copied so each campaign
# owns its own mutable state.
def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")

KIT_FILES = ["ruleset.json", "rules.md", "world-bible.json", "legends.md",
             "sources-and-generators.md", "site-images.json", "chronicler.json"]

def kit_ref(cid):
    ov = _load(campaign_dir(cid) / "campaign-overview.json") or {}
    return ov.get("kit_ref")

def kit_dir(cid):
    kr = kit_ref(cid)
    return campaign_dir(kr) if kr else None

def rag_dir(cid):
    """Dir holding the RAG vectors for this campaign: local if present, else the shared kit."""
    v = campaign_dir(cid) / "vectors"
    if v.exists() and any(v.iterdir()):
        return campaign_dir(cid)
    return kit_dir(cid) or campaign_dir(cid)

def asset_path(cid, relpath):
    """Resolve an asset (e.g. images/sites/x.jpg) local-first, then the shared kit dir."""
    local = campaign_dir(cid) / relpath
    if local.exists():
        return local
    kd = kit_dir(cid)
    if kd and (kd / relpath).exists():
        return kd / relpath
    return local  # caller 404s

def create_fbl_campaign(display_name, character=None, template="forbidden-lands"):
    """Create a fresh Forbidden Lands campaign that starts at Hex I20 with Weatherstone
    known only by rumor. Shares the template's RAG + site art via kit_ref; copies the
    small kit files; carries canon NPCs/plots scrubbed of the template's playthrough."""
    from json_ops import atomic_write_json
    import fbl_create
    char = fbl_create.build_from_spec(character or {})
    slug = _slug(display_name) or _slug(char.get("name")) or "new-adventure"
    dest = campaign_dir(slug)
    if dest.exists():
        raise ValueError(f"A campaign folder '{slug}' already exists.")
    src = campaign_dir(template)
    if not src.exists():
        raise ValueError(f"Kit template '{template}' not found.")
    dest.mkdir(parents=True)
    (dest / "images").mkdir(exist_ok=True)
    (dest / "saves").mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    nowiso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for f in KIT_FILES:                                   # 1) copy small shared kit files
        if (src / f).exists():
            shutil.copy2(src / f, dest / f)

    npcs = _load(src / "npcs.json") or {}                 # 2) canon, scrubbed of prior play
    for v in npcs.values():
        if isinstance(v, dict):
            v["events"] = []
    atomic_write_json(dest / "npcs.json", npcs)
    plots = _load(src / "plots.json") or {}
    for v in plots.values():
        if isinstance(v, dict):
            v["events"] = []
    atomic_write_json(dest / "plots.json", plots)
    cons = _load(src / "consequences.json") or {"active": [], "resolved": []}
    cons["resolved"] = []
    atomic_write_json(dest / "consequences.json", cons)
    facts = _load(src / "facts.json") or {}
    atomic_write_json(dest / "facts.json",
                      {k: facts[k] for k in ("world_building", "plot_local", "plot_regional", "plot_world") if k in facts})

    srcloc = _load(src / "locations.json") or {}          # 3) I20 start; Weatherstone a rumor
    loc = {}
    i20 = srcloc.get("Hex I20 - The Wilds")
    if i20:
        i20 = json.loads(json.dumps(i20))
        i20["connections"] = [c for c in i20.get("connections", []) if "Laboratory" not in (c.get("to") or "")]
        if not any(c.get("to") == "Weatherstone" for c in i20["connections"]):
            i20["connections"].append({"to": "Weatherstone",
                                        "path": "a winding journey through forest and a windswept mountain pass (several Quarter Days)"})
        i20["discovered"] = nowiso
        loc["Hex I20 - The Wilds"] = i20
    for site in ("Weatherstone", "Weatherstone - Watchtower"):
        s = srcloc.get(site)
        if s:
            s = json.loads(json.dumps(s))
            s["discovered"] = False                        # known by legend, not yet found
            loc[site] = s
    atomic_write_json(dest / "locations.json", loc)

    atomic_write_json(dest / "character.json", char)                     # 4) the PC (built above)

    ov = _load(src / "campaign-overview.json") or {}      # 5) fresh overview, kit rules kept
    ov["campaign_name"] = display_name or f"{char.get('name')}'s Forbidden Lands"
    ov["current_character"] = char.get("name")
    ov["session_count"] = 0
    ov["kit_ref"] = template
    ov["player_position"] = {"current_location": "Hex I20 - The Wilds", "previous_location": None, "arrival_time": now}
    ov["time_of_day"] = "morning"
    ov["current_date"] = ov.get("current_date") or "Springrise, Year 1 After the Blood Mist"
    atomic_write_json(dest / "campaign-overview.json", ov)

    (dest / "session-log.md").write_text(                 # 6) fresh log
        f"# {ov['campaign_name']}\n\nStart: Hex I20 - The Wilds. {char.get('name')} "
        f"({char.get('race')} {char.get('class')}) sets out, drawn by rumors of the castle Weatherstone.\n",
        encoding="utf-8")

    try:                                                  # 7) make it active
        from campaign_manager import CampaignManager
        CampaignManager(str(REPO / "world-state")).set_active(slug)
    except Exception:
        pass
    return slug
