---
slug: json-wrappers-npc
title: --json mode for npc_manager (status/voice read + update write)
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

Wire the shared `cli_output` envelope into npc_manager. Add `--json` for a
representative read (`status`/`voice` — note `voice` already returns a JSON list)
and a representative write (`update`). Normalize on the shared `{"ok","data"}`
envelope.

## Acceptance criteria

- [ ] `status --json` and `voice --json` emit the success envelope (voice data = the lines list).
- [ ] `update --json` emits a structured success/error envelope.
- [ ] Human output unchanged without `--json`.
- [ ] `dm-npc.sh` passes `--json` through.
- [ ] Tests assert envelope shape for the read and the write (hermetic, DCC fixture).

## Verification

Lane: agent

## Blocked by

json-returning-wrappers

---

## QA Reports

## History

- 2026-06-06T04:10:42Z  created → ready  [ss-tix001]
