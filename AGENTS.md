# AGENTS.md — HackPrinceton F26 team instructions

Shared instructions for every coding agent on this team (Claude Code reads this via CLAUDE.md; Codex/ChatGPT reads it directly). Keep this file the single source of truth for agent rules.

## Hackathon constraints (non-negotiable)
- **Submission deadline: Sunday Nov 15, 2026, 8:00 AM ET** (hard). Devpost.
- Repo must be **public** and **created after Fri Nov 13, 8 PM ET**.
- Live demo is **≤ 2 minutes**: problem, then walkthrough. Optimize for a reliable demo path over breadth.
- Main-track judging: Creativity, Utility, Charity (societal impact), Avidity (polish/passion).

## Where things live
| What | Where |
|---|---|
| Code | This GitHub repo |
| Idea, chosen track, stack, owners, API contracts, decisions | Slack canvas **"HackPrinceton F26 — Spec & Decisions"** (https://hackprincetonavengers.slack.com/docs/T0CHMBYM2VC/F0CHJ5NSHU5) |
| Tasks | Slack list **"HackPrinceton Task Board"** (https://hackprincetonavengers.slack.com/lists/T0CHMBYM2VC/F0CHT5HKW9J) |
| Agent status updates | Slack **#agent-log** |

If you have no Slack access, ask your human to paste the canvas/task info into the session.

## Session protocol
**At start:**
1. Read the Spec & Decisions canvas and the Task Board.
2. Claim exactly one task: set Status → In Progress, fill Branch.
3. Work on a branch named `feat/<short-name>` or `fix/<short-name>`.

**At end:**
1. Commit, push, open a PR (small and frequent).
2. Update the Task Board row (Status, Notes).
3. Post to #agent-log:
   ```
   [Agent: Claude/ChatGPT] [Owner: name]
   ✅ Done: ...
   🌿 Branch / PR: ...
   ⚠️ Blockers / decisions needed: ...
   ➡️ Next: ...
   ```

## Collaboration rules
- **Stay in your area.** Don't edit files owned by another in-progress task; if you must, flag it in #agent-log first.
- **API contracts come from the canvas.** Don't change a shared interface without updating the canvas and announcing it.
- **Decisions made in a private AI chat don't exist** until they're written in the canvas.
- Never commit secrets. Use `.env` (gitignored) and a committed `.env.example`.
- Prefer boring, working tech over clever, fragile tech. Mock external services behind a flag so the demo never depends on flaky Wi-Fi.

## Project details
<!-- Fill in once decided -->
- **Idea:** TBD
- **Main track:** TBD
- **Special tracks:** TBD
- **Stack:** TBD
- **Run locally:** TBD
- **Folder layout:** TBD
