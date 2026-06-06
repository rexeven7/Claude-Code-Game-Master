---
slug: import-voice-capture
title: "Import bible-draft captures author style + real sample_passages"
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: narrative-voice-fidelity
blockedBy: []
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

Ensure an imported book's `world-bible.json` `voice` is actually populated from the
source. In the import bible-draft step (`.claude/commands/import.md`, plus any
helper in `lib/book_bible.py`), the draft must set:
- `voice.style` — a concrete prose fingerprint (sentence rhythm, diction,
  imagery) inferred from the book,
- `voice.sample_passages` — 2-3 SHORT real excerpts of the author's prose pulled
  from the source text (grounding the voice, not invented),
- `voice.vocab` — a few signature in-world terms when present.

This is what `voice-context-surfacing` then feeds to the GM. Keep excerpts short
(fair-use sized) and verbatim from the source.

## Acceptance criteria

- [ ] The import bible-draft instructions explicitly require populating `voice.style` + `voice.sample_passages` (real excerpts) + optional `voice.vocab`
- [ ] A drafted bible from a sample source has a non-empty `voice` with ≥1 sample passage traceable to the source text
- [ ] Drafted bible still passes `world_bible.py validate`
- [ ] `sample_passages` are verbatim source excerpts, not paraphrase/invention (documented in the step)

## Verification

Lane: agent

Run the bible-draft against a small fixture text containing a distinctive voice;
assert the resulting `voice` has a `style` and ≥1 `sample_passages` entry that
appears in the source, and the bible validates.

## Blocked by

None.

---

## QA Reports

## History

- 2026-06-06T20:29:20Z  created → ready  [ship-it]
