---
name: gm-social
description: Social / NPC interaction — KIT-AWARE. Load whenever the player talks to, persuades, reads, or pressures an NPC ("I talk to...", "I ask...", "I convince..."). Use the section matching the active World Kit (ruleset.json `system`): Forbidden Lands / Year Zero Engine (opposed MANIPULATION vs INSIGHT) or D&D 5e (Persuasion/Deception/Intimidation/Insight DCs). NPC memory + consequences persist for every kit.
---

# Social / NPC Interaction (kit-aware)

## Always: load NPC context (any kit)
`bash tools/gm-context.sh "[npc]"` + `bash tools/gm-npc.sh status "[name]"`. Surface the NPC's `goal`, `current_mood`, secret-EXISTENCE (never the text), `bonds`, and `voice`. Most talk needs **no roll** — public info, normal commerce, casual conversation, giving freely. Roll only when the PC tries to bend the NPC against their inclination under real stakes.

---

## Forbidden Lands (Year Zero Engine)

### The mechanic: opposed MANIPULATION vs INSIGHT
- The PC rolls **EMPATHY + Manipulation (+ gear/position dice)**; the NPC resists with **WITS + Insight**. **Each of the NPC's 6s cancels one of the PC's 6s.** Net 1+ success = it lands. **Only the manipulator may push.**
- A success means the NPC **does as asked OR attacks** — but the target **may demand something in return** (a favor, payment, a promise). Manipulation buys compliance, not friendship, and it is remembered.
- **Position modifiers** (each ~ +/-1 skill die): more/visible allies, the request costs them little, you've helped them before, a strong presentation/threat, you hold leverage; against you: insulting, dangerous, or costly asks.
- **Reading an NPC** = the PC's **WITS + Insight** opposed by the NPC's **EMPATHY + Manipulation** (their composure/deceit). Tells the player mood and whether they're being played — not the secret's text.
- Persuade is a **slow** action in combat; Taunt (Performance) is also available. See `gm-combat` for the action economy.

### Reputation & consequences
A manipulator's deeds spread (**Reputation** grows; see `rules.md`). Persist the fallout: `bash tools/gm-npc.sh update "[name]" "[what happened]"`, `gm-npc.sh mood "[name]" "[new mood]"`, and for downstream reactions `bash tools/gm-consequence.sh add "[event]" "[trigger]" [--trigger-type on_npc --match "[name]"]`. **No D&D-style spectacle XP** — note a great social win for the end-of-session XP questions instead.

---

## D&D 5e kit

### Attitude
Friendly (helpful, warm) - Neutral (professional, cautious) - Hostile (dismissive, cold). Derive from history + bonds.

### Social mechanics — when to roll
| Skill | DC (Friendly / Neutral / Hostile) | Use |
|-------|-----------------------------------|-----|
| Persuasion | 10 / 15 / 20 | Change their mind |
| Deception | 10 / 15 / 20 (plausible->outrageous) | Hide truth |
| Intimidation | 10 / 15 / 20 (weak->strong-willed) | Force compliance |
| Insight | opposed vs Deception, or DC 10-20 | Read them |

Modifiers: unreasonable request +5 DC; good rapport -2 DC.

### Persist NPC memory + consequences
`bash tools/gm-npc.sh update "[name]" "[what happened]"` and `gm-npc.sh mood "[name]" "[new mood]"`. Positive/negative reactions -> `bash tools/gm-consequence.sh add "[event]" "[trigger]" [--trigger-type on_npc --match "[name]"]`.

### Reward a social win (award spectacle XP)
A hard persuasion landed, a daring bluff, turning a hostile NPC -> `bash tools/gm-player.sh award --tier minor|major|legendary --reason "..."`. See `gm-craft -> Reward the spectacle`.

---

## Craft (see gm-craft, all kits)
NPCs have agendas, not quests. Don't over-share — secrets revealed slowly are 10x better. NPCs can say no, lie, or give bad advice. Reactions compound across sessions. End with a conversation-ender when they're done.
