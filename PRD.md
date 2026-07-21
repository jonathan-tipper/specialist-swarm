# Incident War-Room — Product Requirements Document

**Status:** Draft for build
**Date:** 2026-07-21
**Owner:** Partner Enablement
**Implementation plan:** [docs/superpowers/plans/2026-07-21-incident-war-room.md](docs/superpowers/plans/2026-07-21-incident-war-room.md)

---

## 1. Summary

An **Incident War-Room** built on the Claude Managed Agents multi-agent API. A PagerDuty-style incident ticket lands; an Incident Commander coordinator fans it out to three specialist sub-agents in parallel — SRE, Security, and Comms — each carrying its own domain Skill. The Commander synthesises their findings into a blameless postmortem document.

The architecture — **coordinator + specialists + skills** — is the same pattern every services firm uses under pressure: one person runs the bridge, specialists own lanes, the commander writes it up. The demo is the visible fan-out on the event stream — three threads spawning at once reads as *everyone jumping on the fire* — plus a real `.docx` postmortem at the end.

This PRD covers building that system on current model versions and current API idioms, correcting the defects carried in the existing prototype.

## 2. Why this scenario

| Property | Effect |
|---|---|
| Stakes are legible without domain briefing | A room full of people understands "the site is down" instantly; nobody needs the pricing context an RFP demands |
| Urgency is intrinsic | The parallel fan-out isn't a technical curiosity — it's obviously the *right* response to an outage |
| Three genuinely different lanes | SRE, Security and Comms produce visibly different artifacts, so the synthesis step has real work to do |
| The output is a document people actually write | Postmortems are universal; the audience recognises the deliverable |

## 3. Goals

| # | Goal | Measure |
|---|---|---|
| G1 | Working end-to-end run from incident ticket in → postmortem `.docx` out | `outputs/postmortem-INC-4417.docx` exists and opens |
| G2 | Visible parallelism during the run | 3 `session.thread_created` events, overlapping `thread_status_running` |
| G3 | Current models throughout | No `claude-opus-4-7` / `claude-sonnet-4-6` / date-suffixed IDs remain |
| G4 | Idempotent setup | Re-running any setup script creates zero duplicate agents/skills |
| G5 | Correct termination | The run never hangs on a tool-confirmation idle and never exits early |
| G6 | Reproducible in 25 minutes by someone who has never seen the repo | Documented order matches script behaviour exactly |
| G7 | Every specialist carries a skill | 3/3 specialists have a custom skill attached — no unexplained gaps |

## 4. Non-goals

- Real incident data or any real service topology — all inputs stay synthetic
- Production hardening (retry policy, observability, secrets beyond `ANTHROPIC_API_KEY`)
- Live integration with PagerDuty, Datadog, or a real status page. The trigger doc is a static file shaped like a PagerDuty payload.
- Stretch goals beyond the postmortem-reviewer critic
- Migrating control-plane setup to version-controlled `ant` CLI YAML. That is the recommended production pattern and is noted in the README as the next step; the workshop keeps Python setup scripts so the flow runs on one toolchain.

## 5. The scenario

**INC-4417 — Checkout API returning 5xx for a subset of regions.**

A synthetic incident with a deliberately ambiguous cause: a config change deployed 40 minutes before onset, *and* an anomalous traffic pattern from a single ASN in the same window. Neither specialist can resolve it alone — SRE sees the deploy, Security sees the traffic, and only the Commander's synthesis reconciles them. That ambiguity is what makes the parallel fan-out earn its place rather than look decorative.

## 6. Roster

| Role | Agent | Model | Skill | Output |
|---|---|---|---|---|
| Coordinator | Incident Commander | `claude-opus-4-8` | `docx` (Anthropic) | The postmortem |
| Specialist | SRE Responder | `claude-sonnet-5` | `severity-runbook` | Root cause hypothesis, mitigation, rollback call |
| Specialist | Security Analyst | `claude-sonnet-5` | `threat-triage` | Attack-or-failure verdict, blast radius, disclosure trigger |
| Specialist | Comms Lead | `claude-sonnet-5` | `status-page-voice` | Customer-facing status update draft |
| Stretch | Postmortem Reviewer | `claude-opus-4-8` | — | PUBLISH / REVISE / ESCALATE verdict |

**On model tiering.** The prior Deal Desk build put one specialist on Haiku to demonstrate cost-appropriate tiering. There is no honest equivalent here — all three war-room outputs are high-stakes, and the Comms draft is the one artifact that could reach customers verbatim. Forcing a cheap model into that slot to make a teaching point would be the wrong call. See §11 for where a Haiku tier *would* legitimately fit if the roster grows.

## 7. Defects inherited from the prototype

The existing code is a Deal Desk. Beyond re-theming, these are the correctness defects it carries. Each maps to a task in the plan.

| # | Defect | Impact | Evidence |
|---|---|---|---|
| D1 | Models are one generation stale | Misses current capability; teaches the wrong IDs | `claude-opus-4-7` in [create_coordinator.py:80](create_coordinator.py:80), `claude-sonnet-4-6` ×3 in [create_specialists.py](create_specialists.py) |
| D2 | Model pinned with a date suffix | Contradicts current guidance to use the bare alias | `claude-haiku-4-5-20251001` at [create_specialists.py:96](create_specialists.py:96) |
| D3 | **No docx skill is ever attached** | The headline deliverable cannot be produced — the coordinator has no `skills` array at all | [create_coordinator.py:76](create_coordinator.py:76) |
| D4 | Idle-break gate is wrong | Run exits on the first transient idle, or hangs waiting on a tool confirmation it never answers | `elif t == "session.status_idle": break` at [run_deal_desk.py:118](run_deal_desk.py:118) — no `stop_reason.type != "requires_action"` check |
| D5 | `setup_environment.py` is undocumented | `run_deal_desk.py` hard-exits without `.environment_id`; the README never mentions the script | README "Core build" vs [run_deal_desk.py:52](run_deal_desk.py:52) |
| D6 | Documented step order contradicts the scripts | Reader is told coordinator-then-skills; scripts say skills-then-coordinator | README step 2/3 vs [create_specialists.py:130](create_specialists.py:130) |
| D7 | Beta header set manually | Redundant and drift-prone — the SDK sets `managed-agents-2026-04-01` automatically on `client.beta.*` | `default_headers={...}` at [create_specialists.py:107](create_specialists.py:107) |
| D8 | Agents re-created on every run | Accumulates orphaned agents, defeats the versioning model | No create-once guard in `create_specialists.py` |
| D9 | Console URL is workspace-less | Links land on "Session not found" for non-default workspaces | [run_deal_desk.py:154](run_deal_desk.py:154) |
| D10 | No retry on session-output listing | Outputs index ~1–3s after idle; a successful run can report "no files found" | [run_deal_desk.py:139](run_deal_desk.py:139) |
| D11 | One specialist had no skill | Scenario card claimed four skills; only three existed | `SKILL_TO_SPECIALIST` at [upload_skills.py:24](upload_skills.py:24) — **resolved by design in this build (G7)** |
| D12 | Zero tests | No way to verify anything without burning a live API run | — |

## 8. Requirements

### 8.1 Trigger document

`synthetic-data/incident-INC-4417.md` — a PagerDuty-style ticket carrying: incident ID, severity, detection source, affected services, error-rate timeseries summary, on-call acknowledgement timestamps, and the raw alert payload. Three supporting files give the specialists something to reason *from* rather than invent:

| File | Primary consumer |
|---|---|
| `service-topology.md` | Security (blast radius), SRE (dependency chain) |
| `recent-changes.json` | SRE (deploy correlation) |
| `past-incidents.json` | Commander (prior-art comparison in the postmortem) |

All four are inlined into the kickoff message — simpler than the Files API at workshop scale, and keeps the whole run inspectable in one place.

### 8.2 Skills

| Skill | Attached to | Contents |
|---|---|---|
| `severity-runbook` | SRE Responder | Severity matrix, SLO burn thresholds, known failure modes, rollback decision criteria |
| `threat-triage` | Security Analyst | Attack-vs-failure decision tree, blast-radius method, IOC checklist, disclosure triggers |
| `status-page-voice` | Comms Lead | Status-update template, tone rules, what may and may not be stated pre-root-cause |
| `docx` (Anthropic pre-built) | Incident Commander | **This is what produces the deliverable** |

### 8.3 Coordinator output

A blameless postmortem `.docx` written to `/mnt/session/outputs/postmortem-INC-4417.docx`, containing:

1. Incident summary (severity, duration, customer impact)
2. Timeline
3. Root cause (from SRE, reconciled with Security)
4. Was this an attack? (from Security, with an explicit verdict)
5. Customer communications issued (from Comms)
6. Contributing factors — blameless framing, no individual named
7. Action items with owners and priority

### 8.4 Idempotency (G4)

All setup scripts read and write a single `.swarm_ids.json`. Present IDs are reused and reported as such. This replaces the current scatter of `.specialist_ids.json`, `.coordinator_id`, `.environment_id`, `.skill_ids.json`, `.last_session_id`.

### 8.5 Run-loop correctness (G5)

The event loop must:
- Open the SSE stream **before** sending the kickoff (already correct — preserve it)
- Break on `session.status_terminated`
- Break on `session.status_idle` **only when** `stop_reason.type != "requires_action"`
- Narrate `session.thread_created` / `thread_status_running` / `thread_message_sent` / `thread_message_received` so the fan-out is visible
- Retry `files.list(scope_id=...)` up to 4 times to absorb output-indexing lag

### 8.6 Testability (D12)

Pure logic lives in a `swarm/` package, testable with no API key and no network:

| Module | Responsibility | Domain-specific? |
|---|---|---|
| `swarm/models.py` | Model ID constants | No |
| `swarm/store.py` | Create-once ID persistence | No |
| `swarm/events.py` | Terminal-state gate, event formatting | No |
| `swarm/context.py` | Document loading and prompt assembly | No |
| `swarm/roster.py` | Agent specs, prompts, skill map | **Yes** — the only module that changes with the scenario |

That split is the point: swapping Deal Desk for War-Room touches `roster.py`, `skills/`, `synthetic-data/`, and one script name. Everything else is scenario-agnostic.

## 9. User flow

```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
pytest                           # verify logic before spending tokens

python setup_environment.py      # 1. cloud environment
python create_specialists.py     # 2. SRE, Security, Comms
python upload_skills.py          # 3. three custom skills, attached
python create_coordinator.py     # 4. Commander + roster + docx skill
python run_war_room.py           # 5. the incident
```

Every script is safe to re-run.

## 10. Success criteria

- [ ] `pytest` passes with no network access and no `ANTHROPIC_API_KEY` set
- [ ] `grep -rE "opus-4-7|sonnet-4-6|haiku-4-5-2025"` returns nothing outside the docs
- [ ] A cold run produces a `.docx` postmortem in `outputs/`
- [ ] The postmortem contains all seven sections from §8.3
- [ ] The postmortem reconciles the deploy *and* the traffic anomaly — not just one (this proves synthesis, not relay)
- [ ] Contributing factors are blameless — no individual named
- [ ] Re-running every setup script twice creates zero duplicates
- [ ] The event stream shows three threads spawned and running concurrently
- [ ] README step order matches the scripts' own "Next:" hints

## 11. Open options (not in scope, cheap to add later)

**A fourth specialist: Timeline Assembler.** Reconstructing an ordered incident timeline from alert payloads and deploy logs is mechanical extraction — the one war-room task genuinely suited to `claude-haiku-4-5`. Adding it would restore four-thread fan-out and the model-tiering teaching point in a role where the cheap tier is the *correct* choice rather than a contrivance. One entry in `SPECIALISTS`, one skill directory, three test lines.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Multi-agent is a research preview; workspace may lack access | README states the prerequisite; scripts surface `403 permission_error` verbatim |
| Commander emits markdown instead of `.docx` | Coordinator prompt names the docx skill, the exact output path, and forbids finishing before the file exists; the run reports explicitly when zero files were produced |
| Commander relays specialist output instead of synthesising | The scenario's dual-cause ambiguity (§5) makes relay visibly insufficient; §10 has an explicit reconciliation criterion |
| Comms draft leaks unconfirmed cause | `status-page-voice` skill states what may not be claimed pre-root-cause; this is the skill's primary job |
| Live verification needs preview access and tokens | All logic tasks verify offline via pytest; only the final task needs a live run |
