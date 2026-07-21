# Option 3 — Incident War-Room

**Concept landed:** Skills, plugins & sub-agents
**Tech:** [Claude Managed Agents multi-agent](https://platform.claude.com/docs/en/managed-agents/multi-agent) + [custom Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) + the pre-built [docx skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/quickstart)
**Time:** 60 minutes
**Output:** An Incident Commander that fans an outage out to three specialists in parallel, each with its own skill, and writes a blameless postmortem as a real Word document.

## The pitch

A PagerDuty alert fires. The checkout API is throwing 5xx across EU and APAC.
Somebody has to run the bridge: get SRE on root cause, get Security on whether
this is an attack, get Comms drafting what customers see — all at once, because
customers are affected right now.

That's the architecture: **coordinator + specialists + skills**. One commander
orchestrates, specialists own lanes, the commander synthesises and writes it up.
Drop the incident in, watch three threads spawn simultaneously on the events
stream, get a postmortem doc out.

The incident is deliberately ambiguous — a config deploy *and* an anomalous
traffic spike in the same window. Neither specialist can resolve it alone. That
is what makes the reconciliation step real work rather than relay.

## Setup (5 min)

You need a workspace API key on the Console. **Multi-agent is currently in
research preview — your workspace may need to be granted access.** If
`create_coordinator.py` returns `403 permission_error`, that's what's missing.
Request access before anything else in this build — it's the one prerequisite
here that isn't in your control.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

If your key is not in your org's Default workspace, also set
`ANTHROPIC_WORKSPACE_ID` so the printed Console links resolve.

Verify the logic layer before spending any tokens:

```bash
pytest
```

## Pick a scenario card

Three cards in [`scenario-cards.md`](./scenario-cards.md). Each gives you a
commander plus a different roster. Pick one. Different teams should pick
different cards.

## Core build (25 min)

Run these **in order**. Every one is safe to re-run — IDs are recorded in
`.swarm_ids.json` and reused, so a second run never creates duplicates.

1. **Provision the environment.** `python setup_environment.py` creates the
   cloud container template the session runs in.

2. **Create the specialists.** `python create_specialists.py` creates three
   sub-agents: SRE Responder, Security Analyst, Comms Lead.

3. **Upload the skills.** `python upload_skills.py` packages the custom skills
   in `skills/` and attaches each to its specialist. All three get one.

4. **Create the commander.** `python create_coordinator.py` creates the Opus 4.8
   Incident Commander with `multiagent: coordinator` config, the specialists in
   its callable roster, and the Anthropic **`docx` skill** — that skill is what
   turns its synthesis into the postmortem document.

5. **Run the incident.** `python run_war_room.py`:
   - Inlines the INC-4417 ticket and supporting documents into the kickoff
     message (no Files API upload — the documents are small enough to inline)
   - Opens the event stream, *then* sends the kickoff
   - Narrates the bridge so you can watch the parallel fan-out
   - Downloads everything the agents produced to `outputs/`

By minute 30 you have a postmortem in `outputs/`, written by a commander who
reconciled three specialists who each used their own skill.

### The roster

| Role | Agent | Model | Skill |
| --- | --- | --- | --- |
| Coordinator | Incident Commander | `claude-opus-4-8` | `docx` |
| Specialist | SRE Responder | `claude-sonnet-5` | `severity-runbook` |
| Specialist | Security Analyst | `claude-sonnet-5` | `threat-triage` |
| Specialist | Comms Lead | `claude-sonnet-5` | `status-page-voice` |
| Stretch | Postmortem Reviewer | `claude-opus-4-8` | — |

## Stretch goals (20 min)

See [`stretch-goals.md`](./stretch-goals.md). The big ones:

- **Postmortem reviewer** — a fourth agent that gates the doc before publication
- **Timeline Assembler** — a Haiku specialist doing mechanical timeline extraction
- **Your own runbook skill** — swap in your firm's real severity matrix
- **Memory across incidents** — the commander recalls similar prior incidents

**Beyond the workshop:** in production, define agents and environments as
version-controlled YAML applied with the `ant` CLI (`ant beta:agents create <
agent.yaml`) and keep only `sessions.create` in application code. The Python
setup scripts here keep the workshop on one toolchain.

## Two-minute demo

Two-monitor setup:
- **Monitor 1:** the bridge narration from `run_war_room.py`. You'll see
  `[on the bridge]` × 3 in quick succession, then three `[investigating]` lines
  overlapping, then `[reported <-]` coming back. The visible simultaneity IS the
  demo — it reads as everyone jumping on the fire at once.
- **Monitor 2:** open the postmortem in `outputs/`. Real document, seven
  sections, blameless, with action items.

Narrate the bridge while it runs. The room will get it immediately — everyone
has been on a call like this.

## What's in this folder

```
specialist-swarm/
├── README.md
├── PRD.md
├── scenario-cards.md
├── stretch-goals.md
├── requirements.txt
├── swarm/                          (all pure logic — unit tested, no network)
│   ├── models.py                   (model IDs)
│   ├── roster.py                   (agent specs + prompts — the only
│   │                                scenario-specific module)
│   ├── context.py                  (document assembly)
│   ├── events.py                   (stream terminal gate + bridge narration)
│   └── store.py                    (create-once ID persistence)
├── tests/                          (run with `pytest` — no API key needed)
├── setup_environment.py            (1. provisions the cloud environment)
├── create_specialists.py           (2. creates SRE, Security, Comms)
├── upload_skills.py                (3. uploads + attaches custom skills)
├── create_coordinator.py           (4. creates the Incident Commander)
├── run_war_room.py                 (5. runs the incident)
├── stretch_critic_subagent.py      (stretch: postmortem reviewer)
├── skills/
│   ├── severity-runbook/SKILL.md   (SRE)
│   ├── threat-triage/SKILL.md      (Security)
│   └── status-page-voice/SKILL.md  (Comms)
└── synthetic-data/
    ├── incident-INC-4417.md        (the trigger)
    ├── service-topology.md         (dependency + blast-radius map)
    ├── recent-changes.json         (24h deploy log)
    └── past-incidents.json         (prior art)
```
