---
name: gm-skills
description: Skill-check resolution — KIT-AWARE judgment framework for when and how to roll. Load whenever the player attempts something uncertain ("I try to..."). Use the section matching the active World Kit (ruleset.json `system`): Forbidden Lands / Year Zero Engine (d6 pool, push, difficulty modifies skill dice, no DC) or D&D 5e (d20 vs DC ladder). Fail-forward philosophy applies to every kit.
---

# Skill Checks (kit-aware)

**When to roll (any kit):** uncertain outcome, real stakes, risk of harm, contested, or time pressure. **Don't roll** for trivial/impossible tasks, routine professional work, or anything with no meaningful consequence for failure. Then use the section for the active kit (`ruleset.json` -> `system`).

---

## Forbidden Lands (Year Zero Engine)

### The roll
- Build a pool of d6: **Attribute (Base) + Skill + Gear**, roll all at once. **Each 6 is a success; one success passes.** Extra 6s add effect (more damage/info/speed per the skill).
- **There is NO difficulty class / target number.** Difficulty instead **adds or removes SKILL dice only** (never base or gear):

  | Trivial +3 | Simple +2 | Easy +1 | Average 0 | Demanding -1 | Hard -2 | Formidable -3 |
  |---|---|---|---|---|---|---|

- **Help:** each present, able ally gives **+1 skill die, max +3.** Declare before rolling.
- **No skill?** Roll **Base + Gear** only. Skills run 0-5; attributes 1-6.
- If a modifier drops skill dice below 0, roll **negative dice** (`--negative N`): each 6 on them **cancels** one success.
- Run it: `uv run python lib/dice.py yze --base <ATTR> --skill <SKILL> --gear <GEAR> [--push] [--artifact 8|10|12] [--negative N]`. In the app, call `roll_dice` and STOP for the player's confirm/push.

### Pushing & Willpower
- Fail (or want more 6s)? **Push once:** reroll every die that is **not a 6 and not a 1** (skill-die 1s are rerolled too — they are never banes).
- After a push, banes activate: each **1 on a Base die** = **1 damage to that attribute + 1 Willpower Point**; each **1 on a Gear die** = the gear bonus **drops 1** (0 = breaks; repair with CRAFTING). WP is 0-10 and fuels talents/magic. You can push a roll only once and **can never break yourself into a critical injury by pushing.**

### Pride & opposed rolls
- **Pride:** once per session, after you **fail** a roll where your Pride applies, add an **Artifact d12** (`--artifact 12`). Still fail -> you **lose** your Pride for a session.
- **Opposed roll:** each of the opponent's 6s cancels one of yours; **only the initiator may push.** Group roll: one PC rolls for all (Stealth uses the **lowest** skill, Scouting the **highest**).
- **Artifact dice:** Mighty d8 / Epic d10 / Legendary d12 replace a normal die and never degrade.

### The 16 skills
| STRENGTH | AGILITY | WITS | EMPATHY |
|---|---|---|---|
| Might | Stealth | Scouting | Manipulation |
| Endurance | Sleight of Hand | Lore | Performance |
| Melee | Move | Survival | Healing |
| Crafting | Marksmanship | Insight | Animal Handling |

### Fail forward (CRITICAL)
A failed roll is never "nothing happens" — it is "something DIFFERENT happens": a cost in time, a new risk, attention drawn, a resource spent, a complication that forks the scene. **Fail-forward is NOT immortality** — when stakes are lethal and telegraphed, "something different" can be death (-> Death Protocol, CLAUDE.md). Don't soften a self-inflicted lethal outcome into a free pass.

### XP is small and player-spent — do NOT auto-award
Forbidden Lands has no D&D-style "spectacle XP." A clever solve is its own reward in the fiction; XP is granted only at **session end** via the questions (`gm-levelup` / `rules.md` Advancement) and **spent** by the player. Do not call the level-scaled `gm-player.sh award`; note great moments and credit them at session end.

---

## D&D 5e kit

### Process
1. Declare the DC BEFORE rolling. 2. Roll `uv run python lib/dice.py "1d20+[mod]"` (or via `game_core.resolve_check`). 3. Narrate by margin.

### DC ladder
Trivial 5 - Easy 10 - Moderate 15 - Hard 20 - Very Hard 25 - Nearly Impossible 30.

### Narrate by margin
Nat 20 = exceptional flourish - beat by 10+ = looks easy, extra benefit - success = clean - fail by 1-4 = close, minor setback - fail by 5+ = clear fail + complication - nat 1 = mishap.

### Reward a great success (award spectacle XP)
A clever/effective/unique solve EARNS progress, not just a kill. On a strong success (nat 20, beat-by-10+, or an inventive approach), grant it before narrating: `bash tools/gm-player.sh award --tier minor|major|legendary --reason "..."` (kit-aware, level-scaled, co-awards followers in DCC). See `gm-craft -> Reward the spectacle`.

### Fail Forward
A failed roll NEVER means "nothing happens" — it means "something DIFFERENT happens." Failed lockpick? The pick breaks inside. Failed persuasion? The NPC shares the info but tips off your enemies. Failed stealth? Not caught yet, but you knocked something over — now you're on a timer. **Fail-forward != immortal**: a catastrophic margin on telegraphed lethal stakes can drop a PC to 0 (-> Death Protocol).

### Failure consequences (by margin below DC)
- Physical: 1-2 minor setback - 3-5 resource spent - 6-9 minor harm (1d4) - 10+ real harm (1d6+).
- Social: 1-2 unconvinced - 3-5 attitude shifts negative - 6-9 acts against you - 10+ hostile/spreads word.
- Information: 1-2 partial - 3-5 nothing, try another way - 6-9 wrong conclusion believed true - 10+ triggers a ward/wastes time.
For significant failures: `bash tools/gm-consequence.sh add "[what happens]" "[when]" [--trigger-type ...]`.

### Common skills by ability
STR: Athletics - DEX: Acrobatics/Sleight of Hand/Stealth - INT: Arcana/History/Investigation/Nature/Religion - WIS: Animal Handling/Insight/Medicine/Perception/Survival - CHA: Deception/Intimidation/Performance/Persuasion.
