---
name: gm-combat
description: Combat resolution — KIT-AWARE. Load when a hostile action is declared or combat starts. Use the section that matches the active World Kit (ruleset.json `system`): Forbidden Lands / Year Zero Engine (dice pools, initiative cards 1-10, one slow + one fast action, attribute damage, armor dice, critical injuries, monster attacks) OR D&D 5e (d20 initiative, AC/HP, XP-by-CR, death saves). Persist with `bash tools/gm-combat.sh`.
---

# Combat Mechanics (kit-aware)

**Check the active kit first** (`ruleset.json` -> `system`). If it is **Year Zero Engine / Forbidden Lands**, use the FBL section. If it is **dnd5e**, use the D&D section. Other kits resolve through the generic core (`lib/game_core.py`) and the kit's own `rules.md`. Persist HP/attributes/initiative with `bash tools/gm-combat.sh` (start/add-enemy/hp/condition/next-turn/end) so the fight survives resumes.

---

## Forbidden Lands (Year Zero Engine)

No HP, no AC, no rounds-of-attrition math. The **four attributes are the health tracks**; you hit on **one 6**; damage knocks points off an attribute; **0 = Broken**. Telegraph lethal fights, then let the dice fall (see Stakes below).

### Initiative
- Draw/roll initiative **once** at the start of the fight: each combatant gets a number **1-10** (cards, or `uv run python lib/dice.py "1d10"`). **1 acts first**, order is fixed for the whole fight.
- **Surprise:** the surprised side draws 2 and keeps the worst; the ambusher may get a free action.
- A monster may be dealt **2-3 initiative cards** to act multiple times per round (that is what makes it terrifying).

### The turn: one Slow + one Fast action (or two Fast)
- **Slow:** Slash, Stab, Punch/Kick/Bite, Grapple, Break Free, Shoot, Persuade (Manipulation), Taunt (Performance), Cast a Spell, Flee, Crawl, Charge.
- **Fast:** Dodge, Parry, Draw Weapon, Get Up, Shove, Disarm, Feint, Run, Retreat, Ready Weapon, Aim, Power Word, Use Item.
- Helping another costs an action of the same type.

### Range (zones)
Arm's Length (adjacent) - Near (same zone) - Short (<=25 m, next zone) - Long (<=100 m) - Distant (line of sight). RUN (fast) moves one zone; if an enemy is at Arm's Length you must RETREAT (Move roll) instead.

### Attacks
- **Melee** = `STR (base) + Melee (skill) + weapon (gear)`. **Ranged** = `AGI + Marksmanship + weapon`. **Hit = at least one 6.**
- **Damage = the weapon's Damage rating + 1 per EXTRA 6.** Damage hits **Strength** unless stated otherwise.
- **Ranged range mods (to skill dice):** Arm's Length -3 (or **+3** vs a defenseless/unaware target), Near 0, Short -1, Long -2, Distant -3 (requires Aim first).
- In the app, call `roll_dice` (base=attr, skill=skill, gear=weapon, name it MELEE/MARKSMANSHIP) and **STOP** — the player confirms, rolls, may push, then you narrate from the returned successes. Apply damage with `update_character` BEFORE narrating.

### Defense (reactive; costs the defender an action)
- **Dodge:** roll **Move**; each 6 cancels one of the attacker's 6s. You fall prone unless you accept -2 to stay up. **+2 vs a Slash.**
- **Parry:** roll **Melee** + shield/weapon bonus; -2 if the weapon lacks the Parrying quality. Shields can parry **ranged**; bare weapons cannot.
- A prone target gives standing attackers **+2**.

### Armor (vs Strength damage only)
When a Strength hit lands, the defender rolls **Gear dice = Armor Rating**; **each 6 reduces the damage by 1**. Armor is not an action and **cannot be pushed**. Each **1** (only if damage got through) drops the Armor Rating by 1. Helmets add to body armor.

| Armor | AR | | Weapon | Dmg / Bonus |
|---|---|---|---|---|
| Leather | 2 | | Knife/Dagger | 1 / +2 |
| Studded Leather | 3 | | Sword (1-h) | 2 / +2 |
| Chainmail | 6 (3 vs Stab/arrow) | | Broadsword/Battleaxe | 2-3 / +1-2 |
| Plate | 8 (Move -2) | | Two-handed sword/axe | 3 / +1 |
| Small / Large Shield | +1 / +2 (parry) | | Spear (reach) | 2 / +2 |
| Cover: door 4 - tree 5 - wall 8 (vs ranged) | | | Helmets: open 2 - closed 3 - great 4 (Scout -2) | |

### Broken, Critical Injuries, Death
- **Broken** (an attribute hits 0): out of the fight in that mode. STR/AGI -> can only **crawl**; WITS -> **panicked** (may flee only); EMP -> **breakdown**.
- **Critical injury:** when **Strength is Broken** (or **Wits**, via the Horror table) roll **D66** on the table for the latest damage type (Slash / Blunt / Stab / Horror). Some entries are **LETHAL** (a successful HEALING roll must beat the timer or the character dies); a few are **instant death** (e.g. cleft/crushed/skewered skull, pierced heart, heart attack from fright). **Pushing NEVER inflicts a critical injury** - you can't kill yourself by pushing.
- **Coup de grace** on a defenseless intelligent foe: fail an EMPATHY roll, spend 1 WP, take 1 EMP damage (waived by Cold-Blooded).
- **Recovery:** a successful HEALING roll restores points = successes (one attempt per healer). Unaided, 1 point back after D6 hours; a Quarter Day of Rest/Sleep restores the rest - unless a Condition blocks it.

### Monsters are different
Monsters add a **Monster Attack** (roll/choose on their D6 table) - a **slow action at Arm's Length** unless stated, +1 damage per extra 6, **cannot be pushed**. Monsters **don't weaken when wounded** (their Strength is just how much damage they can take; a Broken monster is dead/dying with no crit roll). They are **immune to fear** and to Wits/Empathy attacks, generally **cannot be parried (only dodged)**, and never parry. Spawn the `monster-manual` agent for stat blocks (book-first via RAG / Book of Beasts roster).

### Dice quick-reference
```
# Melee: Strength 4, Melee 2, broadsword (+2): one 6 hits, damage 2 + extra 6s
uv run python lib/dice.py yze --base 4 --skill 2 --gear 2
# Push it (banes activate: 1s on base = STR damage + WP; 1s on gear degrade the weapon)
uv run python lib/dice.py yze --base 4 --skill 2 --gear 2 --push
```

### Stakes (read this)
A **loseable** game. Telegraph lethal threats ("this is far beyond you"), give an out, never kill on one unlucky roll in a trivial moment - but reckless play against over-matched foes, ignored warnings, or a tightening string of failures **can and should** kill. On PC death, run the **Death Protocol** (CLAUDE.md): persist -> narrate -> offer the hand-off. The session does not end.

---

## D&D 5e kit

Persist combat with `bash tools/gm-combat.sh` (start/add-enemy/hp/condition/next-turn/end) so HP and initiative survive resumes.

### Flow
1. Get enemy stats (`features/dnd-api/monsters/dnd_monster.py "[creature]" --combat` or quick: AC 13, HP 15, +3, 1d6+1).
2. Initiative: `uv run python lib/dice.py "1d20+[dex]"` per combatant; order high->low.
3. Each turn: attack `1d20+bonus` vs AC; on hit roll damage; update HP via `gm-combat.sh hp`.
4. Resolution: award XP, handle loot (persist BEFORE narrating), advance time.

### XP by Challenge Rating
| CR | XP | CR | XP | CR | XP |
|----|-----|----|----|----|----|
| 0 | 10 | 4 | 1,100 | 10 | 5,900 |
| 1/8 | 25 | 5 | 1,800 | 11 | 7,200 |
| 1/4 | 50 | 6 | 2,300 | 13 | 10,000 |
| 1/2 | 100 | 7 | 2,900 | 15 | 13,000 |
| 1 | 200 | 8 | 3,900 | 17 | 18,000 |
| 2 | 450 | 9 | 5,000 | 20 | 25,000 |
| 3 | 700 | | | | |

Bonus: clever tactics +25%, creative environment +10-25%, social victory +50%.

**Non-kill wins still earn XP.** When a fight is won WITHOUT a kill — driving the enemy off a ledge, baiting two enemies into each other, an environmental kill, a daring escape from a lethal foe, surviving telegraphed over-CR odds — award it like a kill: `bash tools/gm-player.sh award --tier minor|major|legendary --reason "..."` (kit-aware, level-scaled; co-awards followers in DCC). See `gm-craft -> Reward the spectacle`. Combat's CR->XP is just one source of XP among many.

### Modifiers
Advantage = 2d20 keep high; Disadvantage = keep low. Half cover +2 AC; 3/4 cover +5. Flanking = advantage (melee). Prone: advantage melee / disadvantage ranged. Crit (nat 20) = double damage dice then add mods. Nat 1 = auto-miss.

### Death & Dying
0 HP -> unconscious + death saves (DC 10 Con each turn): 3 successes = stable, 3 failures = death. Nat 20 = 1 HP + conscious. Nat 1 = 2 failures. Damage >= max HP = instant death.
Death is real and reachable — don't fudge saves to keep a doomed PC alive. Telegraph lethal fights first (an over-CR enemy should *read* as deadly), but once the player commits against the odds, let the dice fall. On PC death, run the **Death Protocol** (CLAUDE.md): persist -> narrate -> offer the character hand-off. The session does not end.
