---
name: gm-travel
description: Overland travel & the hex-crawl — KIT-AWARE, FBL-first. Load when the party journeys across the map ("we travel to...", "we head for...", "we make camp", "forage", "hunt", "we push on through the night"). Use the Forbidden Lands / Year Zero Engine journey system (Quarter Days, travel activities, the pathfinder's Survival roll, mishaps, foraging, encounters, getting lost) when that kit is active; a short D&D section covers 5e overland travel.
---

# Travel & the Hex-Crawl (kit-aware)

In Forbidden Lands the **journey IS the adventure** — hunger, cold, and a failed pathfinding roll are as deadly as any sword. Resolve travel here; resolve fights with `gm-combat`, survival Conditions with `gm-conditions`, exploring a site with `gm-dungeon`. Persist movement and the passage of time with `bash tools/gm-session.sh move "[hex/place]"` + `bash tools/gm-time.sh` (these auto-fire consequence ticks and the reactivity check). In the app this is the `move_to` tool.

---

## Forbidden Lands (Year Zero Engine)

### The frame
- The world is a **hex map**; **one hex ~= 10 km**. Rivers are hex borders (ford/bridge/raft/swim to cross). **High Mountains and the Iron Lock are impassable.**
- The day is **four Quarter Days: Morning, Day, Evening, Night.** Light vs darkness shifts by season (winter dark except Day; spring/autumn dark in Evening & Night; summer dark only at Night). **Darkness gives the pathfinder -2.**

### Each Quarter Day, every PC picks ONE activity
| Activity | Who | Hike at same time? | Roll |
|---|---|---|---|
| **Hike** | anyone advancing | — | (movement, below) |
| **Lead the Way** (pathfinder) | one PC | yes | SURVIVAL per new hex |
| **Keep Watch** (lookout) | one PC | yes | SCOUTING on a threat |
| **Forage** | several | no | SURVIVAL (terrain + season) |
| **Hunt** / **Fish** | several (Fish needs water) | no | SURVIVAL then a kill roll |
| **Make Camp** | one rolls | no | SURVIVAL (sets up Rest/Sleep) |
| **Rest** / **Sleep** | several | no | recover / avoid Sleepy |
| **Explore** a site | several | no | see `gm-dungeon` |

### Movement & terrain
| Terrain | Movement | Forage | Hunt |
|---|---|---|---|
| Plains | Open | -1 | +1 |
| Forest | Open | +1 | +1 |
| Dark Forest | Difficult | -1 | 0 |
| Hills | Open | 0 | 0 |
| Mountains | Difficult | -2 | -1 |
| High Mountains | Impassable | - | - |
| Lake / River | boat/raft | - | 0 |
| Marshlands | raft | +1 | -1 |
| Quagmire | Difficult | -1 | 0 |
| Ruins | Difficult | -2 | -1 |

**Hiking distance per Quarter Day:** Open terrain **2 hexes on foot, 3 mounted**; Difficult **1 hex** (foot or mounted). Forage/Hunt are also modified by **season** (Spring -1, Summer 0, Autumn +1, Winter -2).

**Forced march:** hike 2 Quarter Days freely. A **3rd** requires an **ENDURANCE** roll (fail -> 1 AGILITY damage and you must Rest/Sleep that Quarter). A **4th** is ENDURANCE at **-2** and **automatically makes you Sleepy** (`gm-conditions`).

### Lead the Way (the pathfinder)
Appoint one pathfinder when the party moves. **Each NEW hex entered -> the pathfinder rolls SURVIVAL** (Pathfinder talent and terrain/darkness modify it). **No roll to re-enter a hex you have already visited.** On a **failure you still enter the hex but suffer a mishap** — roll **D66**:

| D66 | Mishap |
|---|---|
| 11-12 | **Quicksand** — Might to escape, 1 AGI per fail; no progress |
| 13-21 | **Blocked Terrain** — Might/Move, 1 STR per fail; no progress |
| 22-26 | **Lost** — no progress; one SURVIVAL roll per Quarter to find the way out |
| 31-32 | **Sprained Ankle** — pathfinder takes a blunt-trauma critical injury |
| 33-34 | **Torn Clothes** — roll for COLD; Crafting to mend |
| 35-36 | **Landslide** — Move or take a 4-base-dice attack (WD 1, blunt) |
| 41-45 | **Downpour** — roll for COLD; no progress |
| 46-52 | **Fog** — -1 hex (stuck in difficult terrain); 1 EMPATHY damage each |
| 53-54 | **Wasps' Nest** — Move or a 4-base-dice attack (AGILITY damage) |
| 55-61 | **Mosquito Swarm** — 4-base-dice attack (EMPATHY damage) |
| 62-64 | **Savage Animal** — GM picks from the animal table |
| 65-66 | **Persistent Animal** — a small nuisance animal tails the party |

Roll it with `uv run python lib/dice.py "1d66"` (or 2d6 read as tens+units). **Getting Lost** stops progress until a SURVIVAL roll finds the way (one attempt per Quarter Day).

### Keep Watch & random encounters
The lookout may **Keep Watch and Hike together** (but not also Lead the Way, unless traveling solo). The GM rolls on the **random-encounter table once per Quarter Day while hiking, once per day when stationary**. On a threat the lookout makes a straight **SCOUTING** roll (opposed only if actively ambushed); success spots it at a safe distance. Spawn `monster-manual` for any creature; resolve a fight via `gm-combat`.

### Forage / Hunt / Fish / Make Camp (brief)
- **Forage** (SURVIVAL, terrain+season): success -> Vegetables/water = successes; failure -> a foraging mishap (D6: poison / leeches / sprained ankle / torn clothes / savage or persistent animal).
- **Hunt** (needs a ranged weapon/trap): SURVIVAL to find prey, roll the prey on a D6 table, then a **kill roll** (Marksmanship/Survival, modified by the animal). A boar fights back.
- **Fish** (needs water + gear): SURVIVAL + gear -> Fish = successes; mishaps on a D6.
- **Make Camp** (one PC rolls SURVIVAL, Quartermaster talent helps): on a **failure the GM secretly rolls a D66 camp mishap to spring later** (spoiled water, rotten food, bad campsite = no Sleep, downpour, the fire dies, a campfire spreads, vermin, lost or broken gear). A camp still needs a **night sentry** (Keep Watch) — combat voids Rest/Sleep. **Bare Ground** (no camp) means everyone rolls SURVIVAL or gets Sleepy, and risks COLD.

Track food/water/arrows/torches as **Resource Dice** (D6-D12): each use, roll; a 1-2 steps the die down (D8->D6); it depletes at D6. Persist consumption and any damage with `gm-player.sh` / `update_character`.

### Sea travel
Like land travel, but the **skipper** rolls **SURVIVAL (+ Sailor talent)** per new hex; failure -> a sea mishap (navigational error / squall / whirlpool / leak / overboard / grounding).

---

## D&D 5e kit
Overland travel by pace (slow/normal/fast: 18/24/30 miles per day), navigation via Survival vs a DC (fast pace -5 to passive Perception, can't track), foraging Survival DC 10/15/20 by terrain, and weather/exhaustion (`gm-conditions`). Advance time and fire consequences with `gm-session.sh move` + `gm-time.sh`.
