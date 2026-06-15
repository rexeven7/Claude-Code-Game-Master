"""Forbidden Lands creation tools — the generator tables, as on-demand rolls.

Everything here is grounded in the player's OWN material, not invented:
  - monster (build) rolls the REAL D66 demon tables (GM's Guide p.84-88),
    extracted to fbl_tables.json by extract_fbl_tables.py.
  - monster (pick) rolls the REAL Book of Beasts D66 roster, then RAGs the
    creature's real stat block.
  - legend picks a REAL legend from the catalog (proper nouns from the books)
    and RAGs its real prose from the Legends PDF.
  - npc / site roll the canonical FBL taxonomy (kin, profession, site type) and
    pull the descriptive specifics from the books via RAG.

When the RAG index is reachable (the user's machine) every result is enriched
with real passages; in a no-RAG environment the dice + real tables still stand.
"""
from __future__ import annotations
import json
import random
from pathlib import Path
import engine

_TABLES = {}
try:
    _TABLES = json.loads((Path(__file__).resolve().parent / "fbl_tables.json").read_text(encoding="utf-8"))
except Exception:
    _TABLES = {}

# ----------------------------------------------------------------- RAG enrich
def _rag(cid, query, k=2):
    try:
        from lib.rag.rag_extractor import RAGExtractor
        rx = RAGExtractor(str(engine.rag_dir(cid)))
        if rx.vector_store.count() <= 0:
            return []
        return [(h.get("text") or "").strip().replace("\n", " ")[:400]
                for h in rx.query(query, n_results=k) if h.get("text")]
    except Exception:
        return []

# ----------------------------------------------------------------- D66 helpers
def roll_d66():
    return f"{random.randint(1,6)}{random.randint(1,6)}"

def _ord(code2):
    return int(code2[0]) * 6 + int(code2[1])

def _match(roll, table):
    """Return the table row whose D66 code/range contains the roll (real book ranges)."""
    r = _ord(roll)
    best = None
    for row in table:
        c = row["code"].replace("–", "-")
        if "-" in c:
            lo, hi = c.split("-", 1)
            if _ord(lo) <= r <= _ord(hi):
                return row
        elif _ord(c) == r:
            return row
        if _ord(c.split("-")[0]) <= r:      # fallback: last row at/below the roll (roster has gaps)
            best = row
    return best or (table[0] if table else None)

def _roll_expr(expr):
    """Resolve a book dice expression like 'D6+3' or 'D6' to a number; pass through plain ints."""
    if not expr:
        return None
    s = str(expr).upper().replace(" ", "")
    if s in ("-", "—"):
        return 0
    base = 0
    if "D6" in s:
        n = s.count("D6") or 1
        if s.startswith("2D6"):
            n = 2
        base = sum(random.randint(1, 6) for _ in range(max(1, n)))
        plus = s.split("+")[1] if "+" in s else "0"
        try:
            base += int(plus)
        except ValueError:
            pass
        return base
    try:
        return int(s)
    except ValueError:
        return None

# ----------------------------------------------------------------- legends
# Proper nouns straight from the Legends compendium / legends.md (real, not invented).
_LEGENDS = {
    "treasure": ["Clay's Rosary", "Queen Agatha's Twin Tablets", "Barkhyde", "Arrows of the Fire Wyrm",
                 "Feroxa's Claws", "Scarnesbane", "Carskenfoot's Boots", "Phantom Daggers", "Wyrm's Key",
                 "Voller's Helmet", "The Nightwalker's Hourglass", "The Tezaur", "Wail's Horn",
                 "Well of Tears", "Menkaura's Tooth", "Tvedra's Twin Rings"],
    "crown":    ["The Stanengist Crown", "The Maligarn Sword", "The Nekhaka Scepter", "The Blood Star Cloak Clasp"],
    "site":     ["The Hollows", "Weatherstone", "Vale of the Dead", "Grindbone", "Ravenhole", "Amber's Peak",
                 "Eye of the Rose", "Pelagia", "Stonegarden", "Stoneloom Mines", "Haggler's House"],
    "figure":   ["Merigall", "Krasylla", "Virelda Bloodbeak", "Zertorme", "Arvia of Crombe",
                 "Empress Soria of Urhur", "Kalman Rodenfell", "Rust Prince Kartorda"],
}
_TELLERS = ["a one-eyed wanderer by the fire", "a dying soldier's last breath", "a drunk in a ruined tavern",
            "an old water-stained map", "an old woman who sells charms", "a captured bandit, bargaining",
            "a half-remembered children's song", "a hermit who has not spoken in years"]

def gen_legend(cid):
    category = random.choice(list(_LEGENDS))
    title = random.choice(_LEGENDS[category])
    teller = random.choice(_TELLERS)
    passages = _rag(cid, f"{title} legend")
    real = passages[0] if passages else ""
    tale = f"From {teller}, the party hears the legend of **{title}**."
    if real:
        tale += f" {real}"
    return {"kind": "legend", "title": title, "category": category, "teller": teller,
            "passages": passages, "grounded": bool(real),
            "text": f"[A legend reaches the party] {tale}"}

# ----------------------------------------------------------------- monsters
def _build_demon(cid):
    """Roll the REAL GM's Guide demon tables into a stat block."""
    T = _TABLES
    form = _match(roll_d66(), T.get("demon_form", []))

    def _draw(key, allow_multi=True, depth=0):
        row = _match(roll_d66(), T.get(key, []))
        if row and allow_multi and depth < 4 and ("roll" in row["text"].lower() and ("time" in row["text"].lower() or "twice" in row["text"].lower())):
            return [r for _ in range(2) for r in _draw(key, allow_multi, depth + 1)]
        return [row] if row else []

    abilities = _draw("demon_ability")
    attacks = []
    for _ in range(2):                       # the book: "Roll twice on this table."
        attacks += _draw("demon_attack")
    strengths = _draw("demon_strength")
    weakness = _match(roll_d66(), T.get("demon_weakness", []))
    skills = {s: max(0, random.randint(1, 6) - 1) for s in
              ("scouting", "stealth", "move", "lore", "insight", "manipulation")}

    attrs = {}
    if form:
        attrs = {"strength": _roll_expr(form.get("str")), "agility": form.get("agi"),
                 "wits": form.get("wits"), "empathy": form.get("emp")}
        armor = _roll_expr(form.get("armor")) or 0
    else:
        armor = 0
    block = {
        "form": (form or {}).get("form", "Demon"),
        "attributes": attrs, "armor": armor,
        "ability": [a["text"] for a in abilities if a],
        "attacks": [a["text"] for a in attacks if a],
        "strength": [s["text"] for s in strengths if s],
        "weakness": (weakness or {}).get("text", ""),
        "skills": skills,
    }
    name = f"{block['form']} demon"
    text = (f"[Built monster — real GM's Guide tables] A {block['form'].lower()} demon "
            f"(STR {attrs.get('strength')} AGI {attrs.get('agility')} WITS {attrs.get('wits')} "
            f"EMP {attrs.get('empathy')}, Armor {armor}). "
            f"Attacks: {'; '.join(block['attacks']) or 'natural'}. "
            f"Strength: {'; '.join(block['strength']) or '-'}. Weakness: {block['weakness'] or '-'}.")
    return {"kind": "monster", "mode": "build", "name": name, "block": block,
            "source": "GM's Guide — The Demon's Form/Ability/Attacks/Strength/Weakness",
            "passages": [], "text": text}

def gen_monster(cid, mode="pick"):
    if mode == "build":
        return _build_demon(cid)
    roll = roll_d66()
    row = _match(roll, _TABLES.get("monster_roster", []))
    name = (row or {}).get("name", "a beast")
    return {"kind": "monster", "mode": "pick", "roll": roll, "name": name,
            "source": "Book of Beasts — D66 monster roster",
            "passages": _rag(cid, f"{name} attributes attack lore resources"),
            "text": f"[Encounter — Book of Beasts D66 {roll}] {name}."}

# ----------------------------------------------------------------- NPCs
# Canonical FBL taxonomy (kin + profession); the specifics come from the books via RAG.
def gen_npc(cid):
    import fbl_create
    kin = random.choice(fbl_create.kins())
    profession = random.choice(fbl_create.professions())
    passages = _rag(cid, f"Forbidden Lands {kin} {profession} NPC name personality")
    flavor = passages[0] if passages else ""
    summary = f"A {kin} {profession}." + (f" {flavor}" if flavor else "")
    return {"kind": "npc", "kin": kin, "profession": profession,
            "passages": passages, "grounded": bool(flavor),
            "source": "GM's Guide / Legends & Adventurers (kin, profession, names)",
            "text": f"[An NPC] {summary}"}

# ----------------------------------------------------------------- sites & treasure
# Canonical adventure-site categories; specifics + named sites come from the books via RAG.
_SITE_TYPES = ["Castle", "Village", "Ruin", "Dungeon", "Tower", "Tomb", "Mine", "Temple", "Camp"]
_RP_SITES = ["Weatherstone", "Vale of the Dead", "Grindbone", "Ravenhole", "Amber's Peak",
             "Eye of the Rose", "Stoneloom Mines", "Haggler's House"]

def gen_site(cid, named=False):
    if named:
        title = random.choice(_RP_SITES)
        passages = _rag(cid, f"{title} adventure site Forbidden Lands")
        body = passages[0] if passages else ""
        return {"kind": "site", "named": True, "title": title, "passages": passages,
                "grounded": bool(body), "source": "Raven's Purge / adventure sites",
                "text": f"[Adventure site] {title}." + (f" {body}" if body else "")}
    stype = random.choice(_SITE_TYPES)
    passages = _rag(cid, f"{stype} adventure site ruin generator who lives inhabitants")
    body = passages[0] if passages else ""
    return {"kind": "site", "named": False, "type": stype, "passages": passages,
            "grounded": bool(body), "source": "GM's Guide — adventure-site / ruin generator",
            "text": f"[Adventure site — a {stype}]" + (f" {body}" if body else "")}

# ----------------------------------------------------------------- dispatch
def generate(cid, kind, **opts):
    if kind == "legend":
        return gen_legend(cid)
    if kind == "monster":
        return gen_monster(cid, mode=opts.get("mode", "pick"))
    if kind == "npc":
        return gen_npc(cid)
    if kind == "site":
        return gen_site(cid, named=bool(opts.get("named")))
    return {"error": f"unknown generator '{kind}'"}
