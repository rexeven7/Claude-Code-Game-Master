"""One-time extractor: pull the REAL Forbidden Lands generator tables out of the
user's own PDFs into fbl_tables.json so the generators roll on the actual book
tables (not invented ones).

Tables captured:
  monster_roster   - Book of Beasts D66 monster roster (p.8)
  demon_form       - GM's Guide "THE DEMON'S FORM" (D66 -> form + STR/AGI/WITS/EMP/ARMOR/effect)
  demon_ability    - GM's Guide "THE DEMON'S ABILITY" (verbatim rows)
  demon_attack     - GM's Guide "THE DEMON'S ATTACKS" (verbatim rows)
  demon_strength   - GM's Guide "THE DEMON'S SPECIAL ABILITY" (verbatim rows)
  demon_weakness   - GM's Guide "THE DEMON'S WEAKNESS" (verbatim rows)

Run:  python3 extract_fbl_tables.py
"""
import json, re, sys
from pathlib import Path
import pdfplumber

SRC = Path(__file__).resolve().parents[2] / "source-material"
GMG = SRC / "Forbidden_Lands_Gamemasters_Guide_5th_printing.r.pdf"
BOB = SRC / "Forbidden_Lands_The_Book_of_Beasts.pdf"
OUT = Path(__file__).resolve().parent / "fbl_tables.json"

CODE = r"\d\d(?:[–\-]\d\d)?"          # a D66 code like 11, 32-34, 11–24
_norm = lambda s: (s or "").replace("’", "'").replace("–", "-")


def _page_text(pdf_path, idx):
    with pdfplumber.open(pdf_path) as pdf:
        return _norm(pdf.pages[idx].extract_text() or "")


def parse_verbatim_rows(block):
    """Group a table block into {code, text} rows: a new row starts at a leading
    D66 code; wrapped continuation lines append to the current row."""
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"\d{2,3}(\s+\d{2,3})*", line):       # page-footer numbers like "82 83"
            continue
        m = re.match(rf"^({CODE})\s+(.*)$", line)
        if m:
            rows.append({"code": m.group(1), "text": m.group(2).strip()})
        elif rows:
            rows[-1]["text"] += " " + line
    return rows


def parse_form(block):
    """FORM rows: code, form-name (multi-word) up to the STR 'D6...' column, then
    AGI/WITS/EMP ints, ARMOR, and the rest is the effect."""
    out = []
    for r in parse_verbatim_rows(block):
        t = r["text"]
        m = re.match(r"^(.*?)\s+(D6[+\d]*)\s+(\d)\s+(\d)\s+(\d)\s+(D6[+\d]*|-|\S+)\s*(.*)$", t)
        if m:
            out.append({"code": r["code"], "form": m.group(1).strip(), "str": m.group(2),
                        "agi": int(m.group(3)), "wits": int(m.group(4)), "emp": int(m.group(5)),
                        "armor": m.group(6), "effect": (m.group(7) or "").strip() or "-"})
        else:
            out.append({"code": r["code"], "form": t, "str": "D6+3", "agi": 3, "wits": 3,
                        "emp": 3, "armor": "D6", "effect": "-"})
    return out


def slice_between(text, start_pat, end_pat):
    s = re.search(start_pat, text, re.I)
    if not s:
        return ""
    rest = text[s.end():]
    e = re.search(end_pat, rest, re.I) if end_pat else None
    return rest[:e.start()] if e else rest


def extract_demon_tables():
    text = "\n".join(_page_text(GMG, i) for i in (84, 85, 86, 87, 88))
    # drop the per-row column headers so they aren't parsed as rows
    text = re.sub(r"(?im)^D66\s+(FORM|ABILITY|ATTACK|STRENGTH|WEAKNESS).*$", "", text)
    form = slice_between(text, r"THE DEMON'S FORM", r"THE DEMON'S ABILITY")
    ability = slice_between(text, r"THE DEMON'S ABILITY", r"THE DEMON'S ATTACKS")
    attack = slice_between(text, r"THE DEMON'S ATTACKS", r"THE DEMON'S SPECIAL ABILITY")
    strength = slice_between(text, r"THE DEMON'S SPECIAL ABILITY", r"THE DEMON'S WEAKNESS")
    weakness = slice_between(text, r"THE DEMON'S WEAKNESS", r"\bSKILLS\b")
    return {
        "demon_form": parse_form(form),
        "demon_ability": parse_verbatim_rows(ability),
        "demon_attack": parse_verbatim_rows(attack),
        "demon_strength": parse_verbatim_rows(strength),
        "demon_weakness": parse_verbatim_rows(weakness),
    }


def extract_monster_roster():
    """The roster column is interleaved with prose; isolate it by word x-position."""
    with pdfplumber.open(BOB) as pdf:
        page = pdf.pages[8]
        words = page.extract_words(use_text_flow=False)
    code_re = re.compile(rf"^{CODE}$")
    codes = [w for w in words if code_re.match(_norm(w["text"]))]
    if not codes:
        return []
    # the table's code column = the most common x0 among code-like words
    from collections import Counter
    col_x = Counter(round(w["x0"]) for w in codes).most_common(1)[0][0]
    codes = [w for w in codes if abs(w["x0"] - col_x) < 6]
    roster = []
    for c in sorted(codes, key=lambda w: w["top"]):
        same = [w for w in words if abs(w["top"] - c["top"]) < 4 and w["x0"] > c["x1"] - 1]
        name = " ".join(_norm(w["text"]) for w in sorted(same, key=lambda w: w["x0"]))
        name = name.strip(" -")
        if name and not name.isupper():        # skip header rows like "MONSTER"
            roster.append({"code": _norm(c["text"]), "name": name})
    return roster


def main():
    tables = {"_source": "Forbidden Lands GM's Guide + Book of Beasts (user PDFs)"}
    tables["monster_roster"] = extract_monster_roster()
    tables.update(extract_demon_tables())
    OUT.write_text(json.dumps(tables, indent=2, ensure_ascii=False), encoding="utf-8")
    for k, v in tables.items():
        if isinstance(v, list):
            print(f"{k:16} {len(v):3} rows")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
