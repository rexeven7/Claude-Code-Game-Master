---
slug: gm-craft-voice
title: "gm-craft narrates to the NARRATIVE VOICE block"
category: enhancement
kind: afk
priority: p1
lane: manual
parentPrd: narrative-voice-fidelity
blockedBy: [voice-context-surfacing]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
createdAt: 2026-06-06T20:29:20Z
updatedAt: 2026-06-06T20:29:20Z
---

## Parent

Narrative Voice Fidelity (prds/narrative-voice-fidelity.md)

## Category

enhancement

## What to build

Close the loop in the narration craft skill. Update `.claude/skills/gm-craft/SKILL.md`
to instruct the GM: when scene context includes a `--- NARRATIVE VOICE ---` block,
treat its `Style` + `sample_passages` as the prose target — match the author's
rhythm, diction, and imagery in narration (distinct from NPC dialogue, which uses
NPC canonical lines). Add a short, concrete reminder to self-check voice when a beat
reads generic.

## Acceptance criteria

- [ ] `gm-craft/SKILL.md` references the `NARRATIVE VOICE` block as the narration prose target
- [ ] Distinguishes world/author prose voice from per-NPC dialogue voice
- [ ] Includes a brief in-voice self-check cue
- [ ] Guidance is concrete (not "write better") — names matching rhythm/diction/imagery to the sample passages

## Verification

Lane: manual

Human-judgement: read the updated craft guidance; confirm it actionably directs the
GM to narrate in the surfaced voice. Live efficacy judged at a /gm dry-run with a
voiced world.

## Blocked by

voice-context-surfacing

---

## QA Reports

## History

- 2026-06-06T20:29:20Z  created → ready  [ship-it]
