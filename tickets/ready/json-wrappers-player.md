---
slug: json-wrappers-player
title: --json mode for player_manager (sheet read + hp/xp/gold/inventory write)
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: dm-claude-reimagining
blockedBy: [json-returning-wrappers]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
createdAt: 2026-06-06T04:10:42Z
updatedAt: 2026-06-06T04:10:42Z
---

## Parent

DM Claude Reimagining (prds/dm-claude-reimagining.md)

## Category

enhancement

## What to build

Wire the shared `cli_output` envelope into player_manager. Add `--json` for a
representative read (character sheet) and a representative write (`hp`). Returning
structured results lets the loop confirm stat changes without scraping text.

## Acceptance criteria

- [ ] A sheet read with `--json` emits the success envelope.
- [ ] `hp --json` (a representative write) emits structured before/after + ok/error.
- [ ] Human output unchanged without `--json`.
- [ ] `dm-player.sh` passes `--json` through.
- [ ] Tests assert envelope shape for the read and the write (hermetic, DCC fixture).

## Verification

Lane: agent

## Blocked by

json-returning-wrappers

---

## QA Reports

## History

- 2026-06-06T04:10:42Z  created → ready  [ss-tix001]
