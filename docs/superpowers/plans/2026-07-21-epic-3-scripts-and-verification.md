# Epic 3 Implementation Plan — Executable scripts, run loop, docs & live verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Epic 1's infrastructure modules and Epic 2's domain content into five runnable scripts, then prove the whole war-room produces `outputs/postmortem-INC-4417.docx` end to end.

**Architecture:** Every script in this epic is a thin I/O shell: parse env, read `.swarm_ids.json`, call one or two `client.beta.*` methods, print a `Next:` line. All logic worth testing already lives in `swarm/` (Epic 1) and `swarm/roster.py` (Epic 2). That split is deliberate — these scripts are verified by one live smoke test (Task G), not by mocking the Managed Agents surface.

**Tech Stack:** Python 3.10+, `anthropic>=0.92.0` SDK (Managed Agents beta `managed-agents-2026-04-01`, Skills beta `skills-2025-10-02`, Files beta `files-api-2025-04-14`), pytest.

**Covers:** GitHub issues [#13](https://github.com/jonathan-tipper/specialist-swarm/issues/13)–[#19](https://github.com/jonathan-tipper/specialist-swarm/issues/19) under epic [#4](https://github.com/jonathan-tipper/specialist-swarm/issues/4).

**Relationship to the master plan:** The verbatim replacement source for each script is already written in [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md), Tasks 9–15. This document does **not** re-copy it — it records the corrections that must be applied to it, and the order to work in. Each task below names the exact line range to copy from.

---

## Check findings

I read the epic, the master plan's Tasks 9–15, and every script currently on disk, then resolved every open question against the installed SDK (`anthropic` 0.117.0). All five are now settled — **C1 is cleared, and C5 turned out to be a live bug, not a theoretical one.**

| # | Finding | Status | Fixed in |
|---|---------|--------|----------|
| **C1** | **Roster wire shape.** The prototype passes `agents: [{"type": "agent", "id": ...}]`; Epic 2's `commander_spec` emits bare ID strings. **Resolved — both are valid.** `BetaManagedAgentsMultiagentParams.agents` is typed `SequenceNotStr[BetaManagedAgentsMultiagentRosterEntryParams]`, which aliases `Union[str, BetaManagedAgentsAgentParams, BetaManagedAgentsMultiagentSelfParams]`. The docstring is explicit: *"Each entry is an agent ID string, a versioned `{"type":"agent","id","version"}` reference, or `{"type":"self"}`."* Epic 2 needs no change. | **Cleared** | — |
| **C2** | **Reviewer append mixes shapes.** Confirmed real, and the reason is sharper than I first thought: the *request* accepts either form, but the *response* never does. `BetaManagedAgentsAgent.multiagent.agents` is typed `List[BetaManagedAgentsAgentReference]` — always resolved Pydantic objects with `id`/`type`/`version`. So `roster + [reviewer_id]` appends a bare `str` to a list of models, then posts that mixed list back as a TypedDict param. | **Confirmed** | Task E, Step 2 |
| **C3** | **Console URL is broken by default.** `.../workspaces/{ANTHROPIC_WORKSPACE_ID or "default"}/sessions/{id}` — the literal string `"default"` is not a workspace ID, so it ships a dead link, printed twice, mid-demo. | **Confirmed** | Task D, Step 2 |
| **C4** | **`anthropic` was not installed.** Now resolved: `.venv` created, `anthropic 0.117.0` installed, comfortably above the `>=0.92.0` floor Epic 1 sets. | **Resolved** | Task 0 |
| **C5** | **`agent.skills` element access — upgraded from Low to a confirmed bug.** `BetaManagedAgentsAgent.skills` is typed `List[Skill]` where `Skill = Union[BetaManagedAgentsAnthropicSkill, BetaManagedAgentsCustomSkill]` — Pydantic models, **not dicts**. So `s.get("skill_id")` raises `AttributeError`, it does not silently no-op. This bug is live in the prototype today (`upload_skills.py:80`): re-running it against any agent that already has a skill attached crashes. | **Confirmed bug** | Task B, Step 2 |

Net effect on sequencing: **nothing blocks the start of this epic.** C1 was the only thing that could have forced a change in Epic 2, and it does not.

### README audit — setup facts the plan was missing

Re-reading the existing `README.md` turned up prerequisites and doc-vs-behaviour mismatches that Tasks 0 and F need to absorb. These are separate from C1–C5.

| # | Finding | Severity | Fixed in |
|---|---------|----------|----------|
| **R1** | **Multi-agent is access-gated.** `README.md:16` — *"multi-agent is currently in research preview — your workspace may need to be granted access."* Nothing in the plan checked this. Task G could fail with a permissions error that looks like a code bug and isn't. | High | Task 0, Step 4 |
| **R2** | **`requirements.txt` pins `anthropic>=0.40.0`.** A clean `pip install -r requirements.txt` can legitimately resolve to a version with no `client.beta.agents` namespace at all — every script dies on import. Epic 1 Task 1 bumps it to `>=0.92.0`; until that lands, follow Task 0's explicit install. | High | Task 0, Step 2 |
| **R3** | **The README's Core build omits `setup_environment.py` entirely** and orders the rest `create_specialists` → `create_coordinator` → `upload_skills`, which is neither what the scripts print nor a working order. Anyone following the README verbatim gets a coordinator whose specialists have no skills, then a run that fails on the missing `.environment_id`. This is D6, and it is worse than "step order is wrong" — a step is missing. | High | Task F, Step 2 |
| **R4** | **`README.md:19` says `cd 03-specialist-swarm`.** This repo's root *is* the project; that directory does not exist. Copy-pasting the setup block fails on line 1. | Medium | Task F |
| **R5** | **README claims the run script "uploads the synthetic RFP as a file"** (`:37`). It does not — `run_deal_desk.py:65-76` inlines the documents into the user message. `run_war_room.py` keeps the inlining approach, so the new README must describe inlining, not the Files API. | Medium | Task F |
| **R6** | **`python-dotenv>=1.0.0` is declared and never imported** by any script. Epic 1's rewritten `requirements.txt` drops it. Confirm that is deliberate rather than an accident, and that no script grows a `load_dotenv()` call expecting it. | Low | Task 0, Step 2 |
| **R7** | **No `.gitignore` exists.** `outputs/` and `.swarm_ids.json` are currently committable, and `.swarm_ids.json` holds live resource IDs. Epic 1 Task 1 creates one; Task G's `git add -A` is dangerous until it does. (`.venv/` is *not* at risk — Python's `venv` writes its own `.gitignore` containing `*`, so it self-ignores. Verified.) | Medium | Task G, Step 9 |

Worth keeping from the old README when Task F rewrites it: the three doc links at `:4` ([multi-agent](https://platform.claude.com/docs/en/managed-agents/multi-agent), [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview), [docx skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/quickstart)), and the two-monitor demo setup at `:56-60` — both are genuinely useful and neither is scenario-specific.

**Dependency reality:** `swarm/` does not exist yet. Tasks A–E all `from swarm.store import IdStore` etc. Neither Epic 1 nor Epic 2 has landed. Task 0 handles this explicitly rather than pretending the epics are parallel.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `setup_environment.py` | Rewrite | Create/reuse the cloud Environment via `IdStore` |
| `create_specialists.py` | Rewrite | Create/reuse the three specialist agents from `SPECIALISTS` |
| `upload_skills.py` | Rewrite | Upload each `skills/*/` bundle, attach to its specialist |
| `create_coordinator.py` | Rewrite | Create/update the Incident Commander — **this is where `docx` is attached** |
| `run_war_room.py` | Create | The demo: stream-first event loop, `is_terminal` gate, output download with retry |
| `run_deal_desk.py` | Delete | Superseded by `run_war_room.py` |
| `download_deliverable.py` | Delete | Logic folded into `run_war_room.download_outputs` |
| `stretch_critic_subagent.py` | Rewrite | Postmortem Reviewer (PUBLISH / REVISE / ESCALATE) |
| `tests/test_models.py` | Modify | Drop the `xfail` marker once every script is clean |
| `README.md`, `scenario-cards.md`, `stretch-goals.md` | Rewrite | War-room framing; step order matched to the scripts' own output |

---

## Task 0: Pre-flight

**Files:** none created — environment and branch setup only.

- [ ] **Step 1: Branch off main**

```bash
git checkout main && git pull
git checkout -b feat/epic-3-scripts-and-run-loop
```

- [ ] **Step 2: Install dependencies**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Expected: `anthropic>=0.92.0` and `pytest>=8.0.0` install cleanly. If `requirements.txt` still reads only `anthropic` with no version pin, Epic 1 Task 1 has not landed — see Step 3.

Verify: `python -c "import anthropic; print(anthropic.__version__)"` → `0.92.0` or higher. Confirmed working at **0.117.0** during the check pass that produced this plan; every SDK type referenced below was read from that version.

**If Epic 1 has not landed, `requirements.txt` still reads `anthropic>=0.40.0` (R2)** — a floor low enough that pip can resolve to a version with no `client.beta.agents` namespace at all, and every script in this epic dies on import. Do not debug that; install explicitly instead:

```bash
pip install "anthropic>=0.92.0" "pytest>=8.0.0"
```

Also note `python-dotenv>=1.0.0` is currently declared but imported by nothing (R6). Epic 1's rewrite drops it. If any script in this epic grows a `load_dotenv()` call, put the dependency back — otherwise leave it dropped.

- [ ] **Step 3: Confirm Epic 1 and Epic 2 have landed**

```bash
python -c "
from swarm.store import IdStore
from swarm.events import is_terminal, describe
from swarm.context import build_context
from swarm.roster import SPECIALISTS, SKILL_TO_SPECIALIST, commander_spec, reviewer_spec
print('epic 1+2 present:', [s.key for s in SPECIALISTS])
"
```

Expected: `epic 1+2 present: ['sre', 'security', 'comms']`

**If this fails with `ModuleNotFoundError: No module named 'swarm'`:** Epics 1 and 2 have not merged. Do **not** stub them — a stub that satisfies an import but returns wrong shapes will let Tasks A–E "pass" their import checks and then fail at Task G, where debugging is expensive because it costs live API calls. Instead:
1. Draft Task F (docs) now — it is the only task in this epic with no `swarm` imports.
2. Ping the Epic 1 and Epic 2 owners with this plan's C1 finding, which they must resolve on their side.
3. Return to Task A once `git log main` shows both epics merged, and rebase this branch onto main.

- [ ] **Step 4: Confirm API access — key *and* multi-agent entitlement (R1)**

```bash
test -n "$ANTHROPIC_API_KEY" && echo "key present" || echo "MISSING — Task G will be blocked"
```

A key alone is not enough. The old README states multi-agent is in research preview and *"your workspace may need to be granted access."* Prove the entitlement now rather than discovering it at Task G, where it will look like a code bug:

```bash
python -c "
from anthropic import Anthropic
c = Anthropic()
print('agents API reachable:', len(list(c.beta.agents.list())), 'existing agents')
"
```

- **Success** (any count, including 0): the workspace is entitled. Proceed.
- **403 / permission or `not_found` error on `beta.agents`:** the workspace lacks multi-agent access. Tasks A–F still proceed — none of them call the API — but **Task G is blocked until access is granted**, so raise that request now. It is the long-lead item in this epic.

Also set the workspace ID if you have it, so the run script prints a deep link rather than the generic one (see C3):

```bash
export ANTHROPIC_WORKSPACE_ID="wrkspc_..."   # optional; from the Console URL
```

---

## Task A: Rewrite `setup_environment.py` and `create_specialists.py`

Closes [#13](https://github.com/jonathan-tipper/specialist-swarm/issues/13). Addresses defects D7 (manual beta header) and D8 (non-idempotent ID files).

**Files:**
- Modify: `setup_environment.py`
- Modify: `create_specialists.py`

- [ ] **Step 1: Replace both files**

Copy verbatim from the master plan:
- `setup_environment.py` ← [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md) lines 1749–1791
- `create_specialists.py` ← same file, lines 1799–1841

No corrections needed to either. Two things to understand rather than change:

- **No `default_headers`.** The prototype set `{"anthropic-beta": "managed-agents-2026-04-01"}` by hand. The SDK sets it on every `client.beta.*` call; setting it manually risks it drifting out of date against the SDK's own value. This is D7.
- **The `def create(spec=spec)` default-argument binding** in `create_specialists.py` is not a style tic. Without it, every closure in the loop captures the same final `spec` by reference and all three agents get created from the last specialist's config.

- [ ] **Step 2: Verify imports and no stale model IDs**

```bash
python -c "import setup_environment, create_specialists; print('ok')"
grep -c "claude-opus-4-7\|claude-sonnet-4-6\|claude-haiku-4-5-2025" setup_environment.py create_specialists.py
```

Expected: `ok`, then `0` for both files.

- [ ] **Step 3: Verify no Deal Desk remnants survive**

```bash
grep -in "deal.desk\|rfp\|pricing\|\.specialist_ids\.json\|\.environment_id" setup_environment.py create_specialists.py
```

Expected: no output. A hit means a stale path or scenario term survived the rewrite.

- [ ] **Step 4: Commit**

```bash
git add setup_environment.py create_specialists.py
git commit -m "refactor: make environment and specialist setup idempotent"
```

---

## Task B: Rewrite `upload_skills.py`

Closes [#14](https://github.com/jonathan-tipper/specialist-swarm/issues/14).

**Files:**
- Modify: `upload_skills.py`

- [ ] **Step 1: Replace the file**

Copy verbatim from [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md) lines 1869–1949.

The idempotency here runs in two directions and both matter: the Skills API rejects a duplicate `display_title` with a 409, so existing skills are listed and reused by title; and an already-attached skill is detected and skipped so re-running never doubles an agent's skill array.

- [ ] **Step 2: Fix the attached-skill check (C5) — this is a real crash, not a hardening**

The copied code does `s.get("skill_id")`, which assumes `agent.skills` holds dicts. It does not: the SDK types it `List[Skill]` where `Skill` is a `Union` of two Pydantic models. `.get()` is not a method on those, so this line raises `AttributeError` the moment it runs against an agent that already has a skill — i.e. on every re-run, which is exactly the idempotency this script exists to provide. The bug is live in the prototype today at `upload_skills.py:80`.

Replace:

```python
        if any(s.get("skill_id") == skill_id for s in current):
```

with:

```python
        if any(getattr(s, "skill_id", None) == skill_id for s in current):
```

`getattr` rather than a bare `s.skill_id` because the `Skill` union covers both `BetaManagedAgentsAnthropicSkill` and `BetaManagedAgentsCustomSkill`, and only custom skills are matched by ID here.

- [ ] **Step 2a: Prove the fix with a regression test**

This is the one place in Epic 3 where a unit test is worth writing — it caught a real bug and costs nothing to pin. Create `tests/test_skill_attach.py`:

```python
from anthropic.types.beta.beta_managed_agents_custom_skill import (
    BetaManagedAgentsCustomSkill,
)

from upload_skills import already_attached


def test_detects_an_attached_custom_skill():
    skills = [BetaManagedAgentsCustomSkill(type="custom", skill_id="skill_abc", version="latest")]
    assert already_attached(skills, "skill_abc") is True


def test_ignores_an_unrelated_skill():
    skills = [BetaManagedAgentsCustomSkill(type="custom", skill_id="skill_abc", version="latest")]
    assert already_attached(skills, "skill_xyz") is False


def test_empty_skill_list_is_not_attached():
    assert already_attached([], "skill_abc") is False
```

Run it and watch it fail with `ImportError` — `already_attached` does not exist yet. Then extract it in `upload_skills.py`:

```python
def already_attached(current_skills, skill_id: str) -> bool:
    """True if skill_id is already on this agent. SDK returns models, not dicts."""
    return any(getattr(s, "skill_id", None) == skill_id for s in current_skills)
```

and call it from `main()`: `if already_attached(current, skill_id):`. Re-run — expected PASS.

If `BetaManagedAgentsCustomSkill`'s constructor signature differs from the above, read the model at `anthropic/types/beta/beta_managed_agents_custom_skill.py` and match its actual fields rather than forcing the test to compile.

- [ ] **Step 3: Verify it imports**

```bash
python -c "import upload_skills; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Verify the skill map matches the directories on disk**

```bash
python -c "
from swarm.roster import SKILL_TO_SPECIALIST
from pathlib import Path
for name in SKILL_TO_SPECIALIST:
    p = Path('skills') / name / 'SKILL.md'
    print(('OK  ' if p.exists() else 'MISS'), p)
"
```

Expected: three `OK` lines for `severity-runbook`, `threat-triage`, `status-page-voice`. A `MISS` means Epic 2's Task 7 did not land — stop and rebase.

- [ ] **Step 5: Commit**

```bash
git add upload_skills.py tests/test_skill_attach.py
git commit -m "refactor: route skill upload and attachment through the ID store

Fixes a live crash: agent.skills holds Pydantic models, not dicts, so the
prototype's s.get('skill_id') raised AttributeError on every re-run."
```

---

## Task C: Rewrite `create_coordinator.py`

Closes [#15](https://github.com/jonathan-tipper/specialist-swarm/issues/15). Addresses defect D3 — the prototype never attached the `docx` skill to the coordinator, so the deliverable could not physically be produced.

**Files:**
- Modify: `create_coordinator.py`
- Possibly modify: `swarm/roster.py`, `tests/test_roster.py` (see Step 1)

- [ ] **Step 1: Note on the roster wire shape (C1) — already resolved, no action needed**

Epic 2's bare-ID-string form is valid. The SDK types `multiagent.agents` as `Union[str, {"type":"agent","id","version"}, {"type":"self"}]` per entry, so `commander_spec`'s `agents: ["agent_a"]` is accepted as-is and `swarm/roster.py` needs no change. Recorded here because the plan originally flagged this as a blocker; it is not.

One asymmetry to carry into Task E: **the request accepts either form, the response only ever returns the object form** (`List[BetaManagedAgentsAgentReference]`). Write bare, read structured.

- [ ] **Step 2: Replace the file**

Copy verbatim from [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md) lines 1974–2025.

Note the create-vs-update branch: agents are persistent, versioned resources. Re-running must produce a *new version* of the existing commander (via `agents.update` with the current `version`), not a second commander. Two coordinators pointing at the same specialists is the failure mode this prevents.

- [ ] **Step 3: Verify the commander spec is correct**

```bash
python -c "
from swarm.roster import commander_spec
s = commander_spec(['agent_x'])
print(s['model'])
print(s['skills'])
print(s['multiagent']['type'])
"
```

Expected:
```
claude-opus-4-8
[{'type': 'anthropic', 'skill_id': 'docx'}]
coordinator
```

If `skills` is empty or missing `docx`, stop. That is defect D3 unfixed, and the entire epic's deliverable depends on it.

- [ ] **Step 4: Verify it imports**

```bash
python -c "import create_coordinator; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add create_coordinator.py swarm/roster.py tests/test_roster.py
git commit -m "feat: attach the docx skill to the commander so it can emit the postmortem

Roster wire shape resolved as <bare strings|wrapped objects> per SDK type
inspection; see C1 in the Epic 3 plan."
```

---

## Task D: Create `run_war_room.py`

Closes [#16](https://github.com/jonathan-tipper/specialist-swarm/issues/16). Addresses defects D4 (premature idle break), D9 (output indexing lag), D10 (duplicated download logic).

**Files:**
- Create: `run_war_room.py`
- Delete: `run_deal_desk.py`, `download_deliverable.py`

- [ ] **Step 1: Create the file**

Copy verbatim from [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md) lines 2065–2217.

**This is the task the epic singles out.** Two ordering constraints in this file are load-bearing and neither is obvious from reading it:

1. **`is_terminal(event)` is checked instead of breaking on `session.status_idle`.** Sessions go idle transiently — between parallel tool calls, and while blocked awaiting a confirmation. The prototype (`run_deal_desk.py:110-112`) broke on the first idle, which in a three-way parallel fan-out means it frequently exits while two specialists are still working. `is_terminal` additionally requires `stop_reason.type != "requires_action"`.
2. **The stream is opened before the kickoff message is sent** (`with ... stream(...)` wraps `events.send`). Reversed, the early events — the ones showing all three specialists spawning at once — arrive buffered in a single batch after the fact, and the fan-out that is the entire point of the demo is invisible.

- [ ] **Step 2: Fix the console URL (C3)**

The copied code emits a dead link when `ANTHROPIC_WORKSPACE_ID` is unset. Replace:

```python
    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID", "default")
    console_url = f"https://platform.claude.com/workspaces/{workspace}/sessions/{session.id}"
```

with:

```python
    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    console_url = (
        f"https://platform.claude.com/workspaces/{workspace}/sessions/{session.id}"
        if workspace
        else f"https://platform.claude.com/sessions/{session.id}"
    )
```

The unqualified form is what the prototype printed, so it is the one shape known to resolve. Set `ANTHROPIC_WORKSPACE_ID` before a live demo to get the deep link.

- [ ] **Step 3: Remove the superseded scripts**

```bash
git rm run_deal_desk.py download_deliverable.py
```

`download_deliverable.py` is fully covered by `download_outputs()`, which additionally retries through the 1–3s output-indexing lag that made the standalone script return "no files found" when run immediately after a session (D9/D10).

- [ ] **Step 4: Verify it imports and the incident data is present**

```bash
python -c "import run_war_room; print('ok')"
python -c "
from pathlib import Path
for p in ['incident-INC-4417.md','service-topology.md','recent-changes.json','past-incidents.json']:
    f = Path('synthetic-data') / p
    print(('OK  ' if f.exists() else 'MISS'), f)
"
```

Expected: `ok`, then four `OK` lines. A `MISS` means Epic 2's Task 8 has not landed — Task G cannot run.

- [ ] **Step 5: Verify the terminal gate is actually wired**

```bash
grep -n "is_terminal\|status_idle" run_war_room.py
```

Expected: exactly one `is_terminal(event)` call, and **no** bare `status_idle` comparison. A literal `session.status_idle` string in this file means the D4 bug came back.

- [ ] **Step 6: Commit**

```bash
git add run_war_room.py
git commit -m "feat: add war-room run loop with correct terminal gate and output retry"
```

---

## Task E: Postmortem reviewer, and clear the stale-model guard

Closes [#17](https://github.com/jonathan-tipper/specialist-swarm/issues/17).

**Files:**
- Modify: `stretch_critic_subagent.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Replace `stretch_critic_subagent.py`**

Copy verbatim from [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md) lines 2251–2327.

- [ ] **Step 2: Make the roster append shape-consistent (C2)**

`commander.multiagent.agents` always comes back as `List[BetaManagedAgentsAgentReference]` — Pydantic models with `id`/`type`/`version`, never bare strings, regardless of which form was sent. So `roster + [reviewer_id]` builds a list of models with one raw `str` on the end and posts it back. Normalise everything to IDs and let `commander_spec` decide the wire shape. Replace:

```python
    client.beta.agents.update(
        commander_id,
        version=commander.version,
        system=system,
        multiagent={"type": "coordinator", "agents": roster + [reviewer_id]},
    )
```

with a rebuild that normalises every entry to whatever shape `commander_spec` produces:

```python
    from swarm.roster import commander_spec

    all_ids = [entry_id(e) for e in roster if entry_id(e)] + [reviewer_id]
    client.beta.agents.update(
        commander_id,
        version=commander.version,
        system=system,
        multiagent=commander_spec(all_ids)["multiagent"],
    )
```

This keeps `swarm/roster.py` as the one place the wire shape is decided, which is what Task C Step 1 settled. If C1 resolves to wrapped objects, this code needs no further change.

- [ ] **Step 3: Remove the xfail marker**

In `tests/test_models.py`, delete the line above `test_no_stale_model_ids_anywhere_in_repo`:

```python
@pytest.mark.xfail(reason="cleared by Tasks 9-13; remove this marker in Task 13", strict=True)
```

Every script that carried `claude-opus-4-7` has now been rewritten, so the repo-wide guard should pass unaided. Delete the `import pytest` line too if nothing else in the file uses it.

- [ ] **Step 4: Run the full suite**

```bash
pytest -v
```

Expected: all pass, `0 xfailed`, `0 xpassed`. If the repo-wide guard fails, its assertion message names the offending file and model ID — fix the file, do not weaken the test.

- [ ] **Step 5: Commit**

```bash
git add stretch_critic_subagent.py tests/test_models.py
git commit -m "feat: add postmortem reviewer and enforce the no-stale-model guard"
```

---

## Task F: Rewrite the docs

Closes [#18](https://github.com/jonathan-tipper/specialist-swarm/issues/18). Addresses defects D5 (README described the Deal Desk scenario) and D6 (documented step order contradicted the scripts' own `Next:` prints).

**Files:**
- Modify: `README.md`
- Modify: `scenario-cards.md`
- Modify: `stretch-goals.md`

This is the only task with no `swarm` imports, so it is the one to draft while blocked on Epics 1 and 2.

- [ ] **Step 1: Replace all three files**

Copy verbatim from [`2026-07-21-incident-war-room.md`](2026-07-21-incident-war-room.md):
- `README.md` ← lines 2360–2519
- `scenario-cards.md` ← lines 2521–2578
- `stretch-goals.md` ← lines 2580–2638

- [ ] **Step 2: Verify the documented step order matches what the scripts print (D6)**

This is the defect, so check it mechanically rather than by eye:

```bash
grep -h "Next: python" *.py
grep -n "python .*\.py" README.md | head -20
```

The chain the scripts print is `setup_environment.py` → `create_specialists.py` → `upload_skills.py` → `create_coordinator.py` → `run_war_room.py`. The README's Core build section must list exactly that order.

The old README (R3) was wrong in two ways, and the second is worse than D6 as originally written: it put `create_coordinator` before `upload_skills` (so specialists ended up with no skills attached), **and it omitted `setup_environment.py` from the Core build entirely** — while the run script requires an environment ID and exits without one. Following the old README verbatim could not work. Check the new one lists all five scripts, in the printed order.

- [ ] **Step 2a: Fix the remaining README inaccuracies (R4, R5)**

Two more things the old README got wrong that a straight scenario-swap would carry over:

- **`cd 03-specialist-swarm` (R4)** — a leftover from when this lived inside a larger hackathon repo. This repo's root *is* the project, so the setup block must not `cd` anywhere. Verify: `grep -n "cd " README.md` returns nothing.
- **"Uploads the synthetic RFP as a file" (R5)** — never true. `run_deal_desk.py` inlined the documents into the user message, and `run_war_room.py` keeps that approach via `build_context`. The new README must say the incident ticket and supporting docs are *inlined into the kickoff message*, not uploaded via the Files API. The Files API is used only in the other direction, to retrieve what the agents wrote.

Carry forward from the old README: the three documentation links (multi-agent, Agent Skills, docx skill) and the two-monitor demo setup. Both are still accurate and neither is Deal-Desk-specific.

- [ ] **Step 2b: State the access prerequisite (R1)**

The old README's one genuinely important setup line was that multi-agent is in research preview and the workspace may need to be granted access. Keep it, and make it more prominent than it was — for a workshop audience it is the difference between "my code is broken" and "my account isn't enabled yet."

- [ ] **Step 3: Verify no Deal Desk language survives anywhere**

```bash
grep -rin "deal desk\|rfp\|acme\|pricing playbook\|run_deal_desk\|download_deliverable" \
  --include="*.md" --include="*.py" . | grep -v "^./PRD.md\|^./docs/"
```

Expected: no output. `PRD.md` and `docs/` legitimately discuss the old scenario as history and are excluded.

- [ ] **Step 4: Commit**

```bash
git add README.md scenario-cards.md stretch-goals.md
git commit -m "docs: rewrite for the incident war-room scenario with corrected step order"
```

---

## Task G: Live end-to-end verification

Closes [#19](https://github.com/jonathan-tipper/specialist-swarm/issues/19). **This is the only task that spends API credit,** and the only verification the five scripts get — they are not unit-tested by design.

**Files:** none modified. This task produces evidence, and possibly bug reports against Tasks A–F.

- [ ] **Step 1: Cold run**

```bash
rm -f .swarm_ids.json
rm -rf outputs/
python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
python run_war_room.py
```

Expected: each script prints `Created ...` then a `Next:` line naming the following script. `run_war_room.py` streams the bridge, then downloads at least one file.

- [ ] **Step 2: Verify the fan-out was actually parallel**

Watch the stream during Step 1, or re-read its output. Expected: three `[tasked ->]` lines for SRE, Security and Comms appearing **before** the first `[reported <-]` line. If they interleave one-at-a-time — task, report, task, report — the commander is working serially and the demo's central claim does not hold. Fix by strengthening the "in parallel" instruction in `COMMANDER_SYSTEM` (Epic 2, `swarm/roster.py`), not here.

- [ ] **Step 3: Verify the deliverable exists and is a real .docx**

```bash
ls -la outputs/
python -c "
import zipfile
z = zipfile.ZipFile('outputs/postmortem-INC-4417.docx')
print('valid docx, parts:', len(z.namelist()))
"
```

Expected: the file exists and opens as a zip with a `word/document.xml` member. If `outputs/` contains only `commander-transcript.txt`, the commander replied in chat instead of invoking `docx` — check that Task C Step 3 really showed the skill attached.

- [ ] **Step 4: Verify synthesis, not relay — the substantive check**

Open the `.docx` and read the root cause section. The scenario is deliberately built with two plausible causes: the `CHG-9912` pool-timeout config change deployed at 13:04 with no canary, and an anomalous single-ASN traffic spike.

Expected: the postmortem **addresses both** — either reconciling them into one causal chain, or explicitly ruling one out with reasoning. `past-incidents.json` contains `INC-4102`, where an identical traffic signature turned out to be a misbehaving partner SDK rather than an attack, so an honest `INCONCLUSIVE` on the security question is a *pass*, not a failure.

A postmortem naming only the config change has relayed the SRE's answer and dropped the Security specialist's. That is the difference between a coordinator and a message bus, and it is the thing this whole build exists to demonstrate. If it fails, the fix is in `COMMANDER_SYSTEM`'s reconciliation instructions (Epic 2), not in these scripts.

- [ ] **Step 5: Verify blameless framing**

```bash
python -c "
import zipfile, re
xml = zipfile.ZipFile('outputs/postmortem-INC-4417.docx').read('word/document.xml').decode()
text = re.sub(r'<[^>]+>', '', xml)
print(text[:2000])
"
```

Expected: no individual is named as at fault. The synthetic data includes on-call acknowledgements with names attached — a postmortem that says "X deployed the change without a canary" fails the blameless standard the commander prompt sets.

- [ ] **Step 6: Verify idempotency — re-run everything**

```bash
python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
```

Expected: every line reads `Reusing`, `already attached ✓`, or `updated in place`. **Nothing** should read `Created` or `Uploaded`. A single `Created` means `IdStore` is not being consulted on that path and a workshop attendee who re-runs a script will silently accumulate duplicate agents.

- [ ] **Step 7: Confirm no duplicates server-side**

```bash
python -c "
from anthropic import Anthropic
c = Anthropic()
names = [a.name for a in c.beta.agents.list()]
for n in sorted(set(names)):
    print(names.count(n), n)
"
```

Expected: count `1` for each of the three specialists and the commander. A count above 1 means an earlier run leaked agents — clean them up before the workshop, since a stale duplicate on the roster produces confusing double-tasking in the event stream.

- [ ] **Step 8: Final gate — the epic's definition of done**

```bash
pytest -v
grep -rn "claude-opus-4-7\|claude-sonnet-4-6\|claude-haiku-4-5-2025" --include="*.py" --include="*.md" . | grep -v "PRD.md\|^./docs/"
```

Expected: all tests pass with zero xfail; grep returns nothing.

- [ ] **Step 9: Commit the evidence**

**Check what is actually untracked before staging anything (R7).** There is no `.gitignore` in the repo today — Epic 1 Task 1 creates one, and if that has not landed, a `git add -A` here sweeps in `outputs/` (including the generated `.docx`) and `.swarm_ids.json` (live resource IDs). `.venv/` is safe either way: Python's `venv` writes its own `.gitignore` containing `*`.

```bash
git status --short
```

Confirm `outputs/` and `.swarm_ids.json` do **not** appear. If they do, add them to `.gitignore` first:

```bash
printf '.venv/\noutputs/\n.swarm_ids.json\n__pycache__/\n' >> .gitignore
git add .gitignore && git status --short
```

Then stage deliberately — never `git add -A` at this step:

```bash
git add .gitignore
git commit -m "chore: end-to-end verification of the incident war-room

Cold run produces outputs/postmortem-INC-4417.docx. Postmortem reconciles
both CHG-9912 and the traffic anomaly. Re-run reports Reusing throughout."
```

The verification evidence lives in the commit message and the epic's checkboxes, not in committed artefacts. `.swarm_ids.json` in particular must stay out of git — it points at live agents in one specific workspace, and committing it means the next person's scripts silently try to reuse resources they cannot see.

---

## Self-review notes

**Epic scope coverage:** Every bullet in issue [#4](https://github.com/jonathan-tipper/specialist-swarm/issues/4)'s Scope maps to a task — setup/specialists → A, skills → B, coordinator+docx → C, run loop → D, reviewer → E, docs → F, live verification → G. All seven sub-issues #13–#19 are covered in order.

**Definition-of-done coverage:** `pytest` zero-xfail → E Step 4 and G Step 8; stale-ID grep → A Step 2, G Step 8; cold run produces the .docx → G Steps 1 and 3; postmortem addresses both causes → G Step 4; re-run reports Reusing → G Step 6; README order matches script prints → F Step 2.

**The epic's "one thing to get right"** — the `stop_reason.type != "requires_action"` gate — is Task D Step 1, with a dedicated mechanical check at Step 5 so it cannot silently regress.

**Deliberate departure from the master plan:** two code corrections (C2 reviewer append, C3 console URL) plus one bug fix with a regression test (C5 skill-entry access). C1 was investigated and cleared — it needs no change in either epic. Every departure is confined to files already in this epic's scope; no cross-epic edit is required.

**Verification standard applied to the check itself:** C1, C2 and C5 were resolved by reading the generated type definitions in `anthropic` 0.117.0 (`types/beta/beta_managed_agents_multiagent_params.py`, `..._multiagent.py`, `..._agent.py`), not by inference from the prototype or from the API docs. C3 is a reasoning result, not an SDK fact — the string `"default"` is self-evidently not a workspace ID. No live API call was made, so nothing here is confirmed against a running session; that remains Task G's job.

**Deliberate non-duplication:** this plan references line ranges in the master plan rather than re-copying ~500 lines of script source. The master plan is committed and stable at `9c2c455`. If it is ever edited, re-check the line ranges before following them — `grep -n "^### Task 9"` and friends will re-locate them.

**README audit coverage:** R1 → Task 0 Step 4 and Task F Step 2b; R2 and R6 → Task 0 Step 2; R3 → Task F Step 2; R4 and R5 → Task F Step 2a; R7 → Task G Step 9.

**Long-lead item:** R1 (multi-agent workspace entitlement) is the only thing here with a turnaround time outside the team's control. It is checked at Task 0 Step 4 precisely so the request goes in on day one rather than on the day someone reaches Task G.

**Known unverified:** everything that can only be proven by a live run — that the commander actually fans out in parallel, actually invokes `docx`, and actually reconciles both causes. Those are Task G Steps 2, 3 and 4, and none of them can be moved earlier. A green `pytest` and a clean set of imports do not mean this epic works; only Task G does.
