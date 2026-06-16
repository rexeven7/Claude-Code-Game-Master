---
name: gm-conditions
description: Status conditions — KIT-AWARE. Load when applying or resolving a condition. Use the section matching the active World Kit (ruleset.json `system`): Forbidden Lands / Year Zero Engine (the four survival Conditions — Hungry/Thirsty/Sleepy/Cold — plus Broken attribute states) or D&D 5e (blinded, charmed, frightened, prone, exhaustion, etc.). Persist via gm-condition.sh (PC) / gm-npc.sh condition (party) / gm-combat.sh condition (enemies).
---

# Conditions (kit-aware)

Check the active kit (`ruleset.json` -> `system`) and use the matching section. Persist with `bash tools/gm-condition.sh` (PC) / `gm-npc.sh condition` (party) / `gm-combat.sh condition` (enemies).

---

## Forbidden Lands (Year Zero Engine)

In FBL the four conditions are about **survival**, not combat status. A PC must **eat, drink, and sleep** each day or grind down. **Track all four after any change** (CLAUDE.md output format): `[ ]Hungry  [ ]Thirsty  [ ]Sleepy  [ ]Cold`. A condition **blocks recovery of its linked attribute(s)** and can kill a Broken character.

| Condition | Onset | Effect |
|---|---|---|
| **HUNGRY** | a day with no food | No STRENGTH recovery (except magic); **-1 STR per week**; if STR Broken while Hungry, **die a week later** without food. |
| **THIRSTY** | a day with no water | **No recovery at all** (except magic); **-1 STR and -1 AGI per day**; if STR or AGI Broken while Thirsty, **die a day later** without water. |
| **SLEEPY** | a day without a Quarter Day's sleep | No WITS recovery; **-1 WITS per day**; if WITS Broken while Sleepy you collapse and must sleep a Quarter Day. |
| **COLD** | failed ENDURANCE vs cold | **Immediately -1 STR and -1 WITS**; keep rolling ENDURANCE (blanket/shelter give gear dice); no STR/WITS recovery until warm; if STR Broken while Cold, **die the next time you must roll**. |

A condition **clears** the moment you eat / drink / sleep a Quarter Day / warm up. Apply the periodic attribute loss as damage via `update_character` (app) or `gm-player.sh`.

### Broken (an attribute at 0)
- **STRENGTH Broken:** down; can only **crawl**; roll a **critical injury** (D66, by damage type) — some lethal/instant.
- **AGILITY Broken:** collapsed from fatigue; can only **crawl**, no actions.
- **WITS Broken:** **panicked** — may flee only; roll on the **Horror** critical table (unless broken by pushing).
- **EMPATHY Broken:** **breakdown** — violent outburst or withdrawal until you recover a point.
- A Break caused **only by a Condition (or by pushing) does NOT trigger a critical injury.** See `gm-combat` for crit tables, recovery, and the Death Protocol.

---

## D&D 5e kit

| Condition | Effect |
|-----------|--------|
| Blinded | Can't see; auto-fail sight checks; disadvantage on attacks |
| Charmed | Can't attack charmer; charmer has advantage on social checks |
| Deafened | Can't hear; auto-fail hearing checks |
| Frightened | Disadvantage while source in sight; can't move closer |
| Grappled | Speed 0 |
| Incapacitated | No actions or reactions |
| Paralyzed | Incapacitated; can't move/speak; auto-fail Str/Dex saves; melee crits |
| Poisoned | Disadvantage on attacks and ability checks |
| Prone | Disadvantage on attacks; melee vs it has advantage |
| Restrained | Speed 0; disadvantage on attacks and Dex saves |
| Stunned | Incapacitated; can't move; barely speak |
| Unconscious | Incapacitated; can't move/speak; unaware; drops prone |

**Unconscious at 0 HP is the dying gate, not death.** It resolves to stable (healed/saves) or dead (kit's death rule). On PC death, persist it and run the Death Protocol (CLAUDE.md).

### Exhaustion
1: disadvantage on ability checks - 2: speed halved - 3: disadvantage on attacks & saves - 4: HP max halved - 5: speed 0 - 6: death.
