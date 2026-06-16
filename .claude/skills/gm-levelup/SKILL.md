---
name: gm-levelup
description: Advancement & progression — KIT-AWARE. Load on a milestone, at session end, or when `gm-player.sh xp` reports LEVEL_UP. Use the section matching the active World Kit (ruleset.json `progression.model`): Forbidden Lands / Year Zero Engine (NO levels — XP is a spendable pool earned from end-of-session questions and spent on skills/attributes/talents) or D&D 5e (XP thresholds, the level-up ceremony). Resource-axis / milestone kits advance per their own ruleset.
---

# Advancement (kit-aware)

Check the active kit's `progression.model` in `ruleset.json`, then use the matching section.

---

## Forbidden Lands (Year Zero Engine) — `xp-levels` as a SPENDABLE pool

**Forbidden Lands has NO character levels.** XP is a small, **spendable** currency the player banks each session and pours into skills, attributes, and talents.

### Earning XP — ask the questions at session end
At the end of every session, ask each player the advancement questions; **roughly +1 XP for each "yes"** (typically **3-8 XP per session**):
- Did you participate in the session?
- Did you explore a **new** location?
- Did you discover something noteworthy, or learn a useful secret/legend?
- Did you overcome a **notable** foe or obstacle?
- Did you act on your **Pride**?
- Did you risk your life for another / for the group?
- Did your **Dark Secret** come into play (for good or ill)?

Grant it **manually**: `bash tools/gm-player.sh xp "[name]" +N` (or `award`/`add` per the tool). **Do NOT use the D&D-scaled "spectacle" auto-award** (`gm-player.sh award --tier ...`) — FBL XP is deliberately small and player-directed. (`gm-player._xp_thresholds` are empty for this kit, so the engine will not announce a "LEVEL_UP".)

### Spending XP (between sessions)
| Buy | Cost |
|---|---|
| Raise a **skill** to a new level | **5 x the new level** XP (level 1 = 5, to 2 = 10, ... to 5 = 25) |
| Raise an **attribute** | steep — GM/ruleset-gated, rare |
| Learn / raise a **talent** (kin, profession, or general) | per the talent (commonly the new rank x cost) |

Skills cap at 5, attributes at the kin maximum. Spending is the player's choice — present what's affordable, then persist the change to `character.json` via `gm-player.sh`. Talents come from the kin/profession lists and the general-talent set (the app's `fbl_creation.json` carries 46 general talents); spawn `create-character` if a new talent needs fleshing out.

### No ceremony, just growth
There is no "ding." A hunter who's been tracking for weeks quietly buys Survival 3; a fighter who survived Weatherstone takes a new Path. Tie purchases to the fiction when you narrate them.

---

## D&D 5e kit

Trigger: when `gm-player.sh xp` outputs **LEVEL_UP**. Thresholds are kit-driven (`player_manager._xp_thresholds`); non-D&D kits do not use this 5e table.

### XP Thresholds
| Level | XP | Milestone |
|-------|------|-----------|
| 1->2 | 300 | first level-up |
| 2->3 | 900 | often subclass |
| 3->4 | 2,700 | first ASI/feat |
| 4->5 | 6,500 | extra attack, 3rd-level spells |
| 5->6 | 14,000 | subclass feature |
| 6->7 | 23,000 | 4th-level spells |
| 7->8 | 34,000 | second ASI/feat |
| 8->9 | 48,000 | 5th-level spells |
| 9->10 | 64,000 | major features |

### Hit Dice by Class
Barbarian d12 - Fighter/Paladin/Ranger d10 - Bard/Cleric/Druid/Monk/Rogue/Warlock d8 - Sorcerer/Wizard d6.

### Ceremony
Announce new level -> roll/average HP + Con mod -> new class features -> spellcasting gains -> ASI/feat at 4/8/12/16/19 (wait for player choice, then edit `abilities` in character.json) -> subclass at level 3.
