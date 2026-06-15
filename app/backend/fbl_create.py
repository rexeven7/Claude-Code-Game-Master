"""Forbidden Lands character creation -- data-driven from the real Player's Handbook.

fbl_creation.json holds the extracted PHB tables (per-profession key attribute, skills,
the 3 profession talents, gear, and the real Pride / Dark Secret option lists; the kin
talents; the general-talents list; and the age point rules). This module exposes:

  options()             -> everything the creation wizard needs (choices + rules)
  build_from_spec(spec) -> a complete character.json from the player's CHOICES
  build_character(...)  -> a quick rules-legal random build (Surprise Me / fallback)

PHB rules honored: attributes 2-4 (key attribute up to 5, or 6 if key for BOTH kin and
profession); skills up to 3 in profession skills at creation; age sets attribute points
(15/14/13), skill points (8/10/12) and general talents (1/2/3); everyone also gets their
kin talent + one chosen profession talent.
"""
from __future__ import annotations
import json
import random
import re
from pathlib import Path

_DATA = json.loads((Path(__file__).resolve().parent / "fbl_creation.json").read_text(encoding="utf-8"))
PROFESSIONS = _DATA["professions"]
KINS = _DATA["kins"]
GENERAL_TALENTS = _DATA["general_talents"]
AGES = _DATA["ages"]
SKILL_ATTR = _DATA["skill_attr"]
ATTRS = ["strength", "agility", "wits", "empathy"]

def _key(skill_display): return skill_display.strip().lower().replace(" ", "_")
SKILL_KEYS = [_key(s) for s in _DATA["skills"]]

LOOK = {
    "Human": {"race": "Human", "species": "human", "hair": "dark, roughly cut", "face": "weathered, common features", "eyes": "wary", "size": "medium"},
    "Half-Elf": {"race": "Half-Elf", "species": "half-elf", "hair": "fair, shoulder-length", "face": "fine-boned, faintly ageless", "eyes": "pale and calm", "size": "medium"},
    "Elf": {"race": "Elf", "species": "elf", "hair": "long and pale", "face": "ageless, fine-boned", "eyes": "deep and unhurried", "size": "medium, slender"},
    "Dwarf": {"race": "Dwarf", "species": "dwarf", "hair": "thick braided beard", "face": "broad, stern, scarred", "eyes": "stone-grey", "size": "short and broad"},
    "Halfling": {"race": "Halfling", "species": "halfling", "hair": "curly", "face": "round and quick", "eyes": "bright", "size": "small"},
    "Goblin": {"race": "Goblin", "species": "goblin", "hair": "sparse, greasy", "face": "sharp, big-eared", "eyes": "yellow, darting", "size": "small, wiry"},
    "Orc": {"race": "Orc", "species": "orc", "hair": "black, matted", "face": "tusked, brutal", "eyes": "red-rimmed", "size": "large and powerful"},
    "Wolfkin": {"race": "Wolfkin", "species": "wolfkin", "hair": "grey pelt and mane", "face": "lupine, long-jawed", "eyes": "amber, feral", "size": "tall and rangy"},
}
ATTR_RULES = {"min": 2, "max": 4, "key_max": 5, "double_key_max": 6}

def kins(): return list(KINS.keys())
def professions(): return list(PROFESSIONS.keys())

def options():
    return {
        "kins": [{"name": k, "key_attribute": v["key"], "talent": {"name": v["talent"][0], "desc": v["talent"][1]}}
                 for k, v in KINS.items()],
        "professions": [{"name": p, "key_attribute": v["key_attribute"], "skills": v["skills"],
                         "talents": v["talents"], "gear": v["gear"], "pride": v["pride"],
                         "dark_secret": v["dark_secret"]} for p, v in PROFESSIONS.items()],
        "general_talents": GENERAL_TALENTS,
        "ages": AGES,
        "skills": _DATA["skills"],
        "skill_attr": SKILL_ATTR,
        "attribute_rules": ATTR_RULES,
    }

def _attr_max(attr, kin, profession):
    k = KINS.get(kin, {}).get("key"); p = PROFESSIONS.get(profession, {}).get("key_attribute")
    if attr == k and attr == p: return ATTR_RULES["double_key_max"]
    if attr in (k, p): return ATTR_RULES["key_max"]
    return ATTR_RULES["max"]

def _legal_attributes(kin, profession, age):
    budget = AGES.get(age, AGES["Adult"])["attribute_points"]
    a = {x: 2 for x in ATTRS}; remaining = budget - 8
    order = sorted(ATTRS, key=lambda x: (-_attr_max(x, kin, profession),))
    i = 0
    while remaining > 0 and any(a[x] < _attr_max(x, kin, profession) for x in ATTRS):
        x = order[i % 4]
        if a[x] < _attr_max(x, kin, profession):
            a[x] += 1; remaining -= 1
        i += 1
    return a

def _default_skills(profession, age):
    budget = AGES.get(age, AGES["Adult"])["skill_points"]
    prof_skills = [_key(s) for s in PROFESSIONS.get(profession, {}).get("skills", [])]
    out = {k: 0 for k in SKILL_KEYS}
    i = 0
    while budget > 0 and prof_skills and any(out[s] < 3 for s in prof_skills):
        s = prof_skills[i % len(prof_skills)]
        if out[s] < 3:
            out[s] += 1; budget -= 1
        i += 1
    return out

def _appearance(kin, sex, profession, given=None):
    base = dict(LOOK.get(kin, LOOK["Human"]))
    appr = {
        "sex": sex or random.choice(["male", "female"]), "age": "adult",
        "race": base.get("race", kin), "species": base.get("species", kin.lower()),
        "hair": base.get("hair", ""), "face": base.get("face", ""), "eyes": base.get("eyes", ""),
        "clothing": profession.lower() + "'s practical garb, worn by the road",
        "gear": ", ".join(PROFESSIONS.get(profession, {}).get("gear", [])[:3]),
        "demeanor": "watchful and road-hardened", "size": base.get("size", "medium"),
    }
    if given:
        appr.update({k: v for k, v in given.items() if v})
    return appr

def _slug(s): return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "hero"

def build_from_spec(spec):
    """Assemble a complete character.json from the player's wizard choices."""
    kin = spec.get("kin") if spec.get("kin") in KINS else "Human"
    profession = spec.get("profession") if spec.get("profession") in PROFESSIONS else "Fighter"
    age = spec.get("age") if spec.get("age") in AGES else "Adult"
    K, P = KINS[kin], PROFESSIONS[profession]
    name = (spec.get("name") or "").strip() or random.choice(_DATA["names"].get(kin, ["Traveler"]))
    sex = spec.get("sex", "")

    attrs = spec.get("attributes") or {}
    attrs = {a: int(attrs.get(a, 0) or 0) for a in ATTRS}
    if sum(attrs.values()) < 8:
        attrs = _legal_attributes(kin, profession, age)
    else:
        attrs = {a: max(ATTR_RULES["min"], min(_attr_max(a, kin, profession), attrs[a])) for a in ATTRS}

    prof_skills = {_key(s) for s in P["skills"]}
    skills = {k: 0 for k in SKILL_KEYS}
    for k, v in (spec.get("skills") or {}).items():
        kk = _key(k)
        if kk in skills:
            cap = 3 if kk in prof_skills else 5
            skills[kk] = max(0, min(cap, int(v or 0)))
    if not any(skills.values()):
        skills = _default_skills(profession, age)

    prof_talent = spec.get("profession_talent") or P["talents"][0]["name"]
    gen = list(spec.get("general_talents") or [])[: AGES[age]["general_talents"]]
    features = ["Kin Talent: " + K["talent"][0] + " -- " + K["talent"][1],
                "Profession Talent: " + prof_talent]
    features += ["Talent: " + g for g in gen]

    pride = (spec.get("pride") or (P["pride"][0] if P["pride"] else "")).strip()
    dark = (spec.get("dark_secret") or (P["dark_secret"][0] if P["dark_secret"] else "")).strip()
    appearance = _appearance(kin, sex, profession, spec.get("appearance"))
    strength = attrs["strength"]

    return {
        "id": _slug(name), "name": name, "race": kin, "class": profession, "level": 1, "age": age,
        "hp": {"current": strength, "max": strength}, "ac": 2,
        "stats": {"str": attrs["strength"], "dex": attrs["agility"], "con": attrs["strength"],
                  "int": attrs["wits"], "wis": attrs["wits"], "cha": attrs["empathy"]},
        "attributes": dict(attrs), "current_attributes": dict(attrs),
        "skills": skills,
        "willpower": {"current": 0, "max": 10},
        "pride": pride, "dark_secret": dark,
        "features": features,
        "inventory": list(P["gear"]), "equipment": [],
        "background": (spec.get("background") or (kin + " " + profession + ", newly walked out of the village into the Forbidden Lands.")).strip(),
        "alignment": "", "bonds": "", "flaws": "", "ideals": "", "traits": "",
        "notes": [], "gold": random.randint(3, 18),
        "xp": {"current": 0, "next_level": 300},
        "visual_appearance": appearance,
        "current_location": "Hex I20 - The Wilds",
    }

def build_character(name="", kin="Human", profession="Fighter", sex="", age="Adult"):
    """Quick rules-legal random build (Surprise Me / backward-compatible)."""
    kin = kin if kin in KINS else "Human"
    profession = profession if profession in PROFESSIONS else "Fighter"
    P = PROFESSIONS[profession]
    spec = {
        "name": name, "kin": kin, "profession": profession, "sex": sex, "age": age,
        "attributes": _legal_attributes(kin, profession, age),
        "skills": _default_skills(profession, age),
        "profession_talent": random.choice(P["talents"])["name"],
        "general_talents": random.sample(GENERAL_TALENTS, AGES.get(age, AGES["Adult"])["general_talents"]),
        "pride": random.choice(P["pride"]) if P["pride"] else "",
        "dark_secret": random.choice(P["dark_secret"]) if P["dark_secret"] else "",
    }
    return build_from_spec(spec)
