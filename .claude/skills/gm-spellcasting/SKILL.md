---
name: gm-spellcasting
description: Magic / spellcasting — KIT-AWARE. Load when a player casts a spell or uses a magical talent. Use the section matching the active World Kit (ruleset.json `system`): Forbidden Lands / Year Zero Engine (Willpower-fueled magic, Power Level = WP spent, magic mishaps) or D&D 5e (Vancian spell slots, save DCs, concentration). Spawn the `spell-caster` agent for spell specifics, grounded book-first.
---

# Spellcasting (kit-aware)

**Check the active kit** (`ruleset.json` -> `system`), then use the matching section. For spell details/lists, spawn the `spell-caster` agent (it resolves book-first from the active kit's source, falling back to the dnd5eapi ONLY for a 5e kit).

---

## Forbidden Lands (Year Zero Engine)

Magic is fueled by **Willpower Points (WP)**, not spell slots. A caster must know the relevant **magic talent** (a Path/discipline — e.g. Path of Healing, Path of Death, Path of Signs, General Magic, Symbolism). The Quickstart only fully details **Path of Healing**; the complete disciplines live in the Player's Handbook + Gamemaster's Guide — **ground every casting in the source via the `spell-caster` agent / RAG**, do not invent spell numbers.

### Casting
- **Spend WP = the spell's Power Level.** Power Level scales the effect (e.g. Path of Healing restores attribute points = Power Level; a *lethal* critical injury needs Power Level 2; curing poison needs Power Level >= Potency / 3).
- **Cast a Spell** is a **slow** action; a **Power Word** is a **fast** action (a single, lesser effect). See `gm-combat` for the action economy.
- A caster cannot spend more WP than they have (cap 10). WP is regained by **pushing** rolls (each 1 on a base die when pushing -> +1 WP) and by rest, per the kit.

### Pushing a spell & Magic Mishaps
- A spell can be **pushed** to raise its Power Level for a bigger effect — but overreaching is dangerous. When a caster pushes a spell (or casts at high Power Level / fumbles), roll on the **Magic Mishap table** (Gamemaster's Guide): results range from minor backlash to catastrophe. Resolve the specific mishap from the book via `spell-caster` / RAG, then persist the fallout (attribute damage, a condition, a consequence).
- Demons and the Blood Mist make sorcery perilous in this world — a Dark Secret about sorcery is a classic hook. Lean into cost and consequence; magic is rare and feared, not a utility belt.

### Persist
Apply WP spent and any damage/condition with `update_character` (app) or `bash tools/gm-player.sh` (CLI) **before** narrating the effect. Record notable castings/mishaps with `gm-note.sh`.

---

## D&D 5e kit

When a player casts a spell: spawn the `spell-caster` agent for details, check slots, resolve.

- **Attack spells:** d20 + spell attack bonus vs AC.
- **Save spells:** target rolls save vs spell save DC (8 + proficiency + casting-ability mod).
- **Utility:** apply effect.

### Spell Slots by Character Level
| Lvl | 1st | 2nd | 3rd | 4th | 5th |
|-----|-----|-----|-----|-----|-----|
| 1 | 2 | - | - | - | - |
| 2 | 3 | - | - | - | - |
| 3 | 4 | 2 | - | - | - |
| 4 | 4 | 3 | - | - | - |
| 5 | 4 | 3 | 2 | - | - |
| 7 | 4 | 3 | 3 | 1 | - |
| 9 | 4 | 3 | 3 | 3 | 1 |

### Concentration
One concentration spell at a time. On damage: Con save DC 10 or half the damage (whichever higher) or lose it. A new concentration spell ends the previous.
