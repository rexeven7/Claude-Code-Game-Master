---
name: gm-dungeon
description: Dungeon / adventure-site exploration — KIT-AWARE. Load when the party enters a cave, ruin, crypt, castle, or underground complex. Lightweight (narrative, default) vs structured (per-room JSON) modes apply to every kit; the FBL section adds the Year Zero Engine site-exploration frame (turns, zones, the Explore activity). For overland/hex travel use `gm-travel`.
---

# Dungeon / Adventure-Site Exploration (kit-aware)

| Mode | Best for |
|------|----------|
| **Lightweight** (default) | Fast, narrative; one master location entry with `internal_layout` + `areas_visited` |
| **Structured** | Tactical/revisited 3+ times; a separate location per room with a `dungeon` field + `exits` + `state` |

### Lightweight flow
Enter -> describe entrance + visible exits -> explore (draw a map only when tactically useful) -> combat by zone -> on exit update master notes if significant.

### Structured flow
Validate exit (exists? locked/secret?) -> handle obstacle (pick/force/key; find secret via Perception/Scouting) -> set destination discovered/visited -> `gm-session.sh move "[Site - Room]"` -> describe (2-4 sentences) + list exits + creatures.

### ASCII map symbols
`@` current - `+` door - `#` locked door - up/down stairs - `~` secret (found) - shaded = fog of war.

---

## Forbidden Lands (Year Zero Engine)

Exploring an adventure site is the **Explore** activity (one of the Quarter-Day travel activities — see `gm-travel`). Inside a site:

- **Time runs in TURNS (~15 minutes each)**, not Quarter Days — use turns to pace light/torches (a torch is a **Resource Die**, roll it down), watches, and wandering threats.
- **You cannot Rest or Sleep in the same Quarter Day you Explore.** Plan recovery for after you withdraw.
- **On entering a room/zone**, the watch-keeper may roll **SCOUTING** to notice threats, traps, or ways out first (Passive awareness otherwise). Darkness imposes -2 and forces MOVE to run / SCOUTING to target (ranged -2) — see `rules.md` Other Hazards.
- **Combat uses zones** (Arm's Length / Near / Short / Long / Distant) — resolve via `gm-combat` (FBL). Many sites are **Cramped** (heavy weapons -2, no Swing).
- **Adventure sites are keyed**: each has its own legend, map, and reactive elements (e.g. Weatherstone's undead rise every full moon). Ground room descriptions in the site's source via `gm-context.sh "[site]"` / RAG; reveal the site map only once the party has actually been there.
- **Treasure & traps:** spawn `loot-dropper` for finds (FBL: coins + gear quality + artifacts, no rarity ladder) and persist with `gm-player.sh` BEFORE the reveal. A disarmed deadly trap or a found secret way is a great moment to note for end-of-session XP.

---

## D&D 5e kit

Standard dungeon turn-based exploration: light/torches by the minute, traps via Perception/Investigation vs DC, locked doors via Thieves' Tools, wandering monster checks. Combat resolves through `gm-combat` (D&D). Award XP for cleared encounters and note non-combat solves for the spectacle award (`gm-craft -> Reward the spectacle`).
