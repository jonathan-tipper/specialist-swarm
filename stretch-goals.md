# Stretch Goals (20 min)

Pick one or two. Each is independently valuable as a demo beat.

## 1. Postmortem reviewer (wired, easiest)

`python stretch_critic_subagent.py` adds a fourth agent that gates the doc
before publication with PUBLISH / REVISE / ESCALATE. Watch it send a REVISE back
and the commander rework the draft — the audience sees quality control happen.

## 2. Timeline Assembler — the Haiku slot

Add a fourth specialist that reconstructs an ordered incident timeline from
alert payloads and the deploy log. It's mechanical extraction, so
`claude-haiku-4-5` is genuinely the right tier — not a cost compromise. Restores
four-thread fan-out and demonstrates model tiering in a role where the cheap
model is the correct choice.

Add one entry to `SPECIALISTS` in `swarm/roster.py`, one skill directory, and
three test lines.

## 3. Your own runbook skill

Replace `skills/severity-runbook/SKILL.md` with your firm's real severity matrix
and rollback criteria. This is the highest-value stretch for a client
conversation — the skill is where institutional knowledge lives, and swapping it
is a two-minute demonstration of exactly that point.

## 4. Memory across incidents

Attach a memory store to the session so the commander accumulates learnings
across runs and consults them on the next incident. Watch it reference INC-3908
unprompted on the second run.

## 5. Escalating severity

Feed a second, worse incident mid-session and watch the commander re-triage
while the first is still open.
