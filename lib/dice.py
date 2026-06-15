#!/usr/bin/env python3
"""
Dice rolling library for the GM harness.

Supports two systems side by side:
  - Standard polyhedral notation: 1d20, 3d6+2, 2d20kh1 (advantage), 2d20kl1 (disadvantage)
  - Year Zero Engine dice pools (Forbidden Lands and other YZE kits): see roll_pool()/yze CLI
"""

import random
import re
from typing import List, Tuple, Dict

# Force UTF-8 stdout/stderr so dice/box glyphs do not crash a legacy Windows (cp1252) console.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Import colors for formatted output
try:
    from lib.colors import Colors, format_roll_result
except ImportError:
    try:
        from colors import Colors, format_roll_result
    except ImportError:
        class Colors:
            RESET = ""; RED = ""; GREEN = ""; YELLOW = ""; CYAN = ""
            BOLD = ""; BOLD_RED = ""; BOLD_GREEN = ""; BOLD_YELLOW = ""; BOLD_CYAN = ""; DIM = ""

        def format_roll_result(notation, rolls, total, is_crit=False, is_fumble=False):
            rolls_str = '+'.join(str(r) for r in rolls)
            return f"\U0001F3B2 {notation}: [{rolls_str}] = {total}"


class DiceRoller:
    def __init__(self):
        self.simple_pattern = re.compile(r'(\d+)d(\d+)([+-]\d+)?')
        self.advantage_pattern = re.compile(r'(\d+)d(\d+)kh(\d+)([+-]\d+)?')
        self.disadvantage_pattern = re.compile(r'(\d+)d(\d+)kl(\d+)([+-]\d+)?')

    def roll(self, notation: str) -> Dict:
        notation = notation.strip()
        match = self.advantage_pattern.match(notation)
        if match:
            count, sides, keep = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(4)) if match.group(4) else 0
            rolls = sorted([random.randint(1, sides) for _ in range(count)], reverse=True)
            kept = rolls[:keep]
            return {'notation': notation, 'rolls': rolls, 'kept': kept, 'discarded': rolls[keep:],
                    'modifier': modifier, 'total': sum(kept) + modifier, 'type': 'advantage'}

        match = self.disadvantage_pattern.match(notation)
        if match:
            count, sides, keep = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(4)) if match.group(4) else 0
            rolls = sorted([random.randint(1, sides) for _ in range(count)])
            kept = rolls[:keep]
            return {'notation': notation, 'rolls': rolls, 'kept': kept, 'discarded': rolls[keep:],
                    'modifier': modifier, 'total': sum(kept) + modifier, 'type': 'disadvantage'}

        match = self.simple_pattern.match(notation)
        if match:
            count, sides = int(match.group(1)), int(match.group(2))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(3)) if match.group(3) else 0
            rolls = [random.randint(1, sides) for _ in range(count)]
            total = sum(rolls) + modifier
            result = {'notation': notation, 'rolls': rolls, 'modifier': modifier, 'total': total, 'type': 'standard'}
            if sides == 20 and count == 1:
                if rolls[0] == 20:
                    result['natural_20'] = True
                elif rolls[0] == 1:
                    result['natural_1'] = True
            return result

        raise ValueError(f"Invalid dice notation: {notation}")

    def format_result(self, result: Dict) -> str:
        if result['type'] in ('advantage', 'disadvantage'):
            kept_str = '+'.join(str(r) for r in result['kept'])
            discarded_str = '+'.join(str(r) for r in result['discarded'])
            mod_str = f" {result.get('modifier', 0):+d}" if result.get('modifier', 0) != 0 else ""
            return f"\U0001F3B2 {result['notation']}: {Colors.CYAN}[{kept_str}]{Colors.RESET} {Colors.DIM}(discarded: {discarded_str}){Colors.RESET}{mod_str} = {Colors.CYAN}{result['total']}{Colors.RESET}"
        is_crit = result.get('natural_20', False)
        is_fumble = result.get('natural_1', False)
        rolls_str = '+'.join(str(r) for r in result['rolls'])
        base = f"\U0001F3B2 {result['notation']}: {Colors.CYAN}[{rolls_str}]{Colors.RESET}"
        if result['modifier'] != 0:
            base += f" {result['modifier']:+d}"
        base += f" = {Colors.CYAN}{result['total']}{Colors.RESET}"
        if is_crit:
            base += f" {Colors.BOLD_GREEN}CRITICAL HIT!{Colors.RESET}"
        elif is_fumble:
            base += f" {Colors.BOLD_RED}CRITICAL MISS!{Colors.RESET}"
        return base


# ====================================================================
# Year Zero Engine dice pools (Forbidden Lands and other YZE kits).
# Base Dice = attribute (banes -> attribute damage + Willpower).
# Skill Dice = skill level (1s are NOT banes; rerolled on a push).
# Gear Dice = gear/weapon bonus (banes -> gear/weapon degraded).
# A 6 is a success; a 1 is a bane that only activates on a push.
# Artifact dice (d8/d10/d12, e.g. a Pride die) add scaled successes.
# Purely additive; the d20/keep notation above is untouched.
# ====================================================================

SUCCESS_MARK = "⚔"        # crossed swords
BANE_MARK = "\U0001F480"       # skull
DIE_MARK = "\U0001F3B2"        # game die


def _artifact_successes(face: int) -> int:
    if face <= 5:
        return 0
    if face <= 7:
        return 1
    if face <= 9:
        return 2
    return 3


def _d6() -> int:
    return random.randint(1, 6)


def roll_pool(base: int = 0, skill: int = 0, gear: int = 0,
              artifact: List[int] = None, negative: int = 0) -> Dict:
    base, skill, gear, negative = max(0, base), max(0, skill), max(0, gear), max(0, negative)
    artifact = list(artifact or [])
    state = {
        'type': 'yze-pool', 'pushed': False,
        'base': [_d6() for _ in range(base)],
        'skill': [_d6() for _ in range(skill)],
        'gear': [_d6() for _ in range(gear)],
        'negative': [_d6() for _ in range(negative)],
        'artifact': [{'size': s, 'face': random.randint(1, s)} for s in artifact],
        'pool_size': base + skill + gear,
    }
    return _score_pool(state)


def push_pool(state: Dict) -> Dict:
    if state.get('pushed'):
        return state
    state['base'] = [f if f in (1, 6) else _d6() for f in state['base']]
    state['gear'] = [f if f in (1, 6) else _d6() for f in state['gear']]
    state['skill'] = [f if f == 6 else _d6() for f in state['skill']]
    state['negative'] = [f if f == 6 else _d6() for f in state['negative']]
    for a in state['artifact']:
        if a['face'] < 6:
            a['face'] = random.randint(1, a['size'])
    state['pushed'] = True
    return _score_pool(state)


def _score_pool(state: Dict) -> Dict:
    successes = (state['base'].count(6) + state['skill'].count(6) + state['gear'].count(6)
                 + sum(_artifact_successes(a['face']) for a in state['artifact']))
    successes -= state['negative'].count(6)
    successes = max(0, successes)
    attr_banes = state['base'].count(1)
    gear_banes = state['gear'].count(1)
    artifact_breaks = sum(1 for a in state['artifact'] if a['face'] == 1) if state['pushed'] else 0
    state['successes'] = successes
    state['success'] = successes > 0
    state['attribute_banes'] = attr_banes if state['pushed'] else 0
    state['gear_banes'] = gear_banes if state['pushed'] else 0
    state['willpower'] = attr_banes if state['pushed'] else 0
    state['artifact_breaks'] = artifact_breaks
    state['can_push'] = not state['pushed']
    return state


def format_pool(state: Dict) -> str:
    def grp(label, faces):
        if not faces:
            return ""
        marked = " ".join(
            f"{Colors.BOLD_GREEN}{f}{SUCCESS_MARK}{Colors.RESET}" if f == 6
            else (f"{Colors.BOLD_RED}{f}{BANE_MARK}{Colors.RESET}" if f == 1 else str(f))
            for f in faces)
        return f"{label}[{marked}] "
    parts = grp("Base", state['base']) + grp("Skill", state['skill']) + grp("Gear", state['gear'])
    if state['negative']:
        parts += grp("Neg", state['negative'])
    for a in state['artifact']:
        mark = SUCCESS_MARK if a['face'] >= 6 else (BANE_MARK if a['face'] == 1 else "")
        parts += f"D{a['size']}[{a['face']}{mark}] "
    head = f"{DIE_MARK} Pushed pool" if state['pushed'] else f"{DIE_MARK} Year Zero pool"
    succ = state['successes']
    line = f"{head} - {parts.strip()} -> "
    line += (f"{Colors.BOLD_GREEN}{succ}{SUCCESS_MARK} success{'es' if succ != 1 else ''}{Colors.RESET}"
             if succ else f"{Colors.BOLD_RED}FAILURE (0 successes){Colors.RESET}")
    if state['pushed']:
        notes = []
        if state['attribute_banes']:
            notes.append(f"{BANE_MARK} -{state['attribute_banes']} attribute (banes)")
        if state['gear_banes']:
            notes.append(f"{BANE_MARK} gear damaged x{state['gear_banes']}")
        if state['willpower']:
            notes.append(f"+{state['willpower']} Willpower")
        if state['artifact_breaks']:
            notes.append(f"artifact breaks x{state['artifact_breaks']}")
        if notes:
            line += "  -  " + " - ".join(notes)
    elif state['can_push']:
        line += f"  {Colors.DIM}(can push){Colors.RESET}"
    return line


_roller = DiceRoller()

def roll(notation: str) -> int:
    return _roller.roll(notation)['total']

def roll_detailed(notation: str) -> Dict:
    return _roller.roll(notation)

def roll_formatted(notation: str) -> str:
    return _roller.format_result(_roller.roll(notation))


def _strip(state):
    return {k: state[k] for k in ('pushed', 'base', 'skill', 'gear', 'negative', 'artifact',
            'successes', 'success', 'attribute_banes', 'gear_banes', 'willpower',
            'artifact_breaks', 'can_push')}


def _main_yze(argv):
    import argparse
    p = argparse.ArgumentParser(prog="dice.py yze", description="Roll a Year Zero (Forbidden Lands) dice pool")
    p.add_argument("--base", type=int, default=0)
    p.add_argument("--skill", type=int, default=0)
    p.add_argument("--gear", type=int, default=0)
    p.add_argument("--artifact", type=int, action="append", default=[])
    p.add_argument("--negative", type=int, default=0)
    p.add_argument("--push", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    state = roll_pool(base=args.base, skill=args.skill, gear=args.gear,
                      artifact=args.artifact, negative=args.negative)
    if args.json:
        import json as _json
        out = {"initial": _strip(state)}
        if args.push:
            out["pushed"] = _strip(push_pool(state))
        print(_json.dumps(out, indent=2))
        return
    print(format_pool(state))
    if args.push:
        print(format_pool(push_pool(state)))


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: dice.py <notation>")
        print("Examples: 1d20, 3d6+2, 2d20kh1 (advantage), 2d20kl1 (disadvantage)")
        print("Year Zero pools: dice.py yze --base 3 --skill 2 --gear 1 [--push] [--artifact 12]")
        sys.exit(1)
    if sys.argv[1] == "yze":
        _main_yze(sys.argv[2:])
        return
    roller = DiceRoller()
    try:
        print(roller.format_result(roller.roll(sys.argv[1])))
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
