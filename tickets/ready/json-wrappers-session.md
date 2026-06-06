---
slug: json-wrappers-session
title: --json mode for session_manager (context/status read + move write)
category: enhancement
kind: afk
priority: p1
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

Wire the shared `cli_output` envelope into session_manager. Add `--json` to its
CLI for a representative read (`status` and/or `context`) and a representative
write (`move`), returning `{"ok", "data"|"error"}`. Preserve human-readable
output as default.

## Acceptance criteria

- [ ] `session_manager.py status --json` and `context --json` emit the success envelope.
- [ ] `move --json` emits a structured success/error envelope.
- [ ] Human output unchanged without `--json`.
- [ ] `dm-session.sh` passes `--json` through.
- [ ] Tests assert envelope shape for the read and the write (hermetic, DCC fixture).

## Verification

Lane: agent

## Blocked by

json-returning-wrappers

---

## QA Reports

## History

- 2026-06-06T04:10:42Z  created → ready  [ss-tix001]
