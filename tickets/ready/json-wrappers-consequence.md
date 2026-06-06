---
slug: json-wrappers-consequence
title: --json mode for consequence_manager (check read + add write)
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

Wire the shared `cli_output` envelope into consequence_manager. Add `--json` for
a representative read (`check`/`check_pending`) and write (`add`). Pairs naturally
with the reactivity-engine work, which wants structured fired-consequence data.

## Acceptance criteria

- [ ] `consequence_manager.py check --json` emits the pending list in the success envelope.
- [ ] `add --json` emits a structured success/error envelope (incl. the new consequence id).
- [ ] Human output unchanged without `--json`.
- [ ] `dm-consequence.sh` passes `--json` through.
- [ ] Tests assert envelope shape for the read and the write (hermetic, DCC fixture).

## Verification

Lane: agent

## Blocked by

json-returning-wrappers

---

## QA Reports

## History

- 2026-06-06T04:10:42Z  created → ready  [ss-tix001]
