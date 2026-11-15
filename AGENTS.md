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
| Tasks | Slack **#tasks** channel (ID `C0CHPFE4490`): one message per task |
| Agent status updates | Slack **#agent-log** |

If you have no Slack access, ask your human to paste the canvas/task info into the session.

## Session protocol
**#tasks format** (keep it exactly like this so every agent can parse it):
- Task = one message: `TASK: <what> | Owner: <name> | Branch: <branch or none>`
- Status = reaction on the task message: 👀 in progress · ✅ done · 🚫 blocked
- Updates, questions, PR links = replies in the task's thread

**At start:**
1. Read the Spec & Decisions canvas and #tasks.
2. Take exactly one task: reply in its thread "taking this, owner: <name>" and add 👀.
3. Work on a branch named `feat/<short-name>` or `fix/<short-name>`.

**At end:**
1. Commit, push, open a PR (small and frequent).
2. Reply in the task's thread with what changed; add ✅ when done (or 🚫 if blocked, with the reason).
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
- **Idea:** MAXIMUS: budget-first venture discovery. Every listed Houston space × 26 business types through building, cash, neighborhood and permit gates, then a sourced per-pick review (see README.md)
- **Main track:** Business & Enterprise (proposed; Jessenth confirms on Devpost)
- **Special tracks:** CoStar, Capital One (Nessie) (proposed)
- **Stack:** Python 3.10+ standard library server (`playground/web.py`), vanilla JS front end (`playground/static/`); Helix (`project helix/`) on its own branches
- **Run locally:** see README.md "Run it"
- **Folder layout:** `playground/` app + tests, `reports/` design notes and write-ups
