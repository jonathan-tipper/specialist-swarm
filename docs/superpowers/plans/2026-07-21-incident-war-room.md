# Incident War-Room Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Managed Agents Incident War-Room — an Incident Commander coordinator that fans a PagerDuty-style outage ticket out to SRE, Security and Comms specialists in parallel, then synthesises a blameless postmortem `.docx`.

**Architecture:** Five thin top-level scripts wrapping a `swarm/` package holding all pure logic. Four of the five `swarm/` modules are scenario-agnostic (models, store, events, context); only `roster.py` encodes the war-room domain. Everything in `swarm/` is unit-tested with no network and no API key; the scripts are verified by one live end-to-end run at the end.

**Tech Stack:** Python 3.10+, `anthropic` SDK (Managed Agents beta), pytest.

**Requirements source:** [PRD.md](../../../PRD.md). Defect IDs (D1–D12) refer to its §7 table.

---

## File Structure

| Path | Responsibility | New/Modified |
|---|---|---|
| `swarm/__init__.py` | Package marker | Create |
| `swarm/models.py` | Model ID constants (D1, D2) | Create |
| `swarm/events.py` | Terminal-state gate + event formatting (D4) | Create |
| `swarm/context.py` | Load incident + supporting docs into a prompt block | Create |
| `swarm/store.py` | Create-once ID persistence in `.swarm_ids.json` (D8) | Create |
| `swarm/roster.py` | War-room agent specs, incl. docx skill (D3, G7) | Create |
| `skills/severity-runbook/SKILL.md` | SRE domain knowledge | Create |
| `skills/threat-triage/SKILL.md` | Security domain knowledge | Create |
| `skills/status-page-voice/SKILL.md` | Comms domain knowledge | Create |
| `synthetic-data/incident-INC-4417.md` | The trigger document | Create |
| `synthetic-data/service-topology.md` | Dependency map | Create |
| `synthetic-data/recent-changes.json` | 24h deploy log | Create |
| `synthetic-data/past-incidents.json` | Prior-art comparisons | Create |
| `tests/test_models.py` | Guards against stale/date-suffixed IDs | Create |
| `tests/test_events.py` | Terminal-gate behaviour | Create |
| `tests/test_context.py` | Document assembly | Create |
| `tests/test_store.py` | Idempotency | Create |
| `tests/test_roster.py` | Spec shape, models, skills | Create |
| `setup_environment.py` | Cloud environment, via store | Modify |
| `create_specialists.py` | Three sub-agents (D7, D8) | Modify |
| `upload_skills.py` | Custom skills + attach | Modify |
| `create_coordinator.py` | Commander + roster + docx skill (D3) | Modify |
| `run_war_room.py` | Run loop (D4, D9, D10) | Create (replaces `run_deal_desk.py`) |
| `stretch_critic_subagent.py` | Postmortem reviewer | Modify |
| `README.md` | Correct order + setup step (D5, D6) | Modify |
| `scenario-cards.md`, `stretch-goals.md` | Re-theme to incident response | Modify |
| Old Deal Desk `skills/`, `synthetic-data/`, `run_deal_desk.py` | — | Delete |

**Testing note.** The five scripts are thin I/O shells over live beta API calls; mocking the whole Managed Agents surface would test the mock. TDD therefore applies to `swarm/` (Tasks 2–6, real red-green cycles); the scripts are covered by the live smoke run in Task 15. Deliberate split, not an omission.

---

### Task 1: Scaffolding

**Files:**
- Create: `swarm/__init__.py`, `tests/__init__.py`, `pytest.ini`, `.gitignore`
- Modify: `requirements.txt`

- [ ] **Step 1: Create directories and package markers**

```bash
mkdir -p swarm tests docs/superpowers/plans
touch swarm/__init__.py tests/__init__.py
```

- [ ] **Step 2: Add pytest to requirements**

Replace the contents of `requirements.txt` with:

```
anthropic>=0.92.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

`0.92.0` is the minimum that types the `scope_id` parameter on `files.list`, which the run script depends on.

- [ ] **Step 3: Add pytest config**

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 4: Add .gitignore**

Create `.gitignore`:

```
.swarm_ids.json
.specialist_ids.json
.coordinator_id
.environment_id
.skill_ids.json
.last_session_id
outputs/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: Install and verify**

Run: `pip install -r requirements.txt && pytest`
Expected: `no tests ran` (exit code 5) — the correct empty-suite state.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini .gitignore swarm/__init__.py tests/__init__.py
git commit -m "chore: add swarm package scaffolding and pytest"
```

---

### Task 2: Model constants (D1, D2)

**Files:**
- Create: `swarm/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
import re
from pathlib import Path

import pytest

from swarm import models

STALE = ("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6", "claude-sonnet-4-5")


def test_commander_is_opus_4_8():
    assert models.COMMANDER == "claude-opus-4-8"


def test_reviewer_is_opus_4_8():
    assert models.REVIEWER == "claude-opus-4-8"


def test_specialist_is_sonnet_5():
    assert models.SPECIALIST == "claude-sonnet-5"


def test_lightweight_tier_is_available_for_future_roles():
    """Unused today (see PRD §11) but defined so a Haiku role has one source."""
    assert models.LIGHTWEIGHT == "claude-haiku-4-5"


def test_no_date_suffixed_ids():
    """Bare aliases only — a trailing -YYYYMMDD is the documented foot-gun."""
    for value in (models.COMMANDER, models.REVIEWER, models.SPECIALIST, models.LIGHTWEIGHT):
        assert not re.search(r"-\d{8}$", value), value


@pytest.mark.xfail(reason="cleared by Tasks 9-13; remove this marker in Task 13", strict=True)
def test_no_stale_model_ids_anywhere_in_repo():
    root = Path(__file__).resolve().parent.parent
    offenders = []
    for path in root.rglob("*.py"):
        if ".git" in path.parts or "tests" in path.parts:
            continue
        text = path.read_text()
        for stale in STALE:
            if stale in text:
                offenders.append(f"{path.relative_to(root)}: {stale}")
    assert not offenders, offenders
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'swarm.models'`

- [ ] **Step 3: Write the implementation**

Create `swarm/models.py`:

```python
"""Model IDs for the Incident War-Room.

Bare aliases only. Never append a date suffix — the alias always resolves to
the current snapshot, and a hand-written suffix will eventually 404.
"""

# Orchestration and synthesis: reconciling three specialist findings into one
# coherent postmortem is the hardest reasoning in the system.
COMMANDER = "claude-opus-4-8"

# Adversarial postmortem review (stretch goal).
REVIEWER = "claude-opus-4-8"

# SRE, Security and Comms. All three war-room outputs are high-stakes — the
# Comms draft could reach customers verbatim — so none is tiered down.
SPECIALIST = "claude-sonnet-5"

# Defined but unused. See PRD §11: a Timeline Assembler doing mechanical
# extraction from alert payloads is where this tier would legitimately fit.
LIGHTWEIGHT = "claude-haiku-4-5"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS — 5 passed, 1 xfailed. The repo-wide guard stays xfail until the old Deal Desk scripts are replaced.

- [ ] **Step 5: Commit**

```bash
git add swarm/models.py tests/test_models.py
git commit -m "feat: pin war-room to current model aliases (Opus 4.8 / Sonnet 5)"
```

---

### Task 3: Event terminal gate (D4)

The current loop breaks on any `session.status_idle`. Sessions idle transiently — between parallel tool executions, and while blocked waiting for a `user.tool_confirmation` or `user.custom_tool_result`. Breaking there truncates the run; never breaking hangs it. The gate must distinguish them via `stop_reason.type`.

**Files:**
- Create: `swarm/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_events.py`:

```python
from types import SimpleNamespace

from swarm.events import describe, is_terminal


def evt(type_, **kwargs):
    return SimpleNamespace(type=type_, **kwargs)


def idle(stop_type):
    return evt("session.status_idle", stop_reason=SimpleNamespace(type=stop_type))


def test_terminated_is_terminal():
    assert is_terminal(evt("session.status_terminated")) is True


def test_idle_end_turn_is_terminal():
    assert is_terminal(idle("end_turn")) is True


def test_idle_retries_exhausted_is_terminal():
    assert is_terminal(idle("retries_exhausted")) is True


def test_idle_requires_action_is_not_terminal():
    """The session is blocked on us — keep the loop alive."""
    assert is_terminal(idle("requires_action")) is False


def test_idle_without_stop_reason_is_terminal():
    """Defensive: a missing stop_reason must not hang the run forever."""
    assert is_terminal(evt("session.status_idle")) is True


def test_running_is_not_terminal():
    assert is_terminal(evt("session.status_running")) is False


def test_agent_message_is_not_terminal():
    assert is_terminal(evt("agent.message", content=[])) is False


def test_describe_thread_created():
    assert describe(evt("session.thread_created", agent_name="SRE Responder")) == (
        "  [on the bridge]    SRE Responder"
    )


def test_describe_thread_running():
    assert describe(evt("session.thread_status_running", agent_name="Comms Lead")) == (
        "  [investigating]    Comms Lead"
    )


def test_describe_delegate():
    assert describe(evt("agent.thread_message_sent", to_agent_name="Security Analyst")) == (
        "  [tasked ->]        Security Analyst"
    )


def test_describe_reply():
    assert describe(evt("agent.thread_message_received", from_agent_name="Security Analyst")) == (
        "  [reported <-]      Security Analyst"
    )


def test_describe_tool_use():
    assert describe(evt("agent.tool_use", name="bash")) == "  [tool: bash]"


def test_describe_unknown_returns_none():
    assert describe(evt("span.model_request_start")) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'swarm.events'`

- [ ] **Step 3: Write the implementation**

Create `swarm/events.py`:

```python
"""Pure helpers for driving a Managed Agents session event stream.

`is_terminal` is the important one. A session goes idle transiently — between
parallel tool executions, or while blocked awaiting a `user.tool_confirmation`
or `user.custom_tool_result`. Breaking on every idle truncates the run.

`describe` uses war-room vocabulary deliberately: during a live demo the
narration should read as an incident bridge, not as an API trace.
"""

TERMINAL_STATUS = "session.status_terminated"
IDLE_STATUS = "session.status_idle"

# Idle with this stop_reason means the session is waiting on the client.
BLOCKED_ON_CLIENT = "requires_action"


def is_terminal(event) -> bool:
    """True when the session is finished and the loop should stop."""
    event_type = getattr(event, "type", None)

    if event_type == TERMINAL_STATUS:
        return True

    if event_type == IDLE_STATUS:
        stop_reason = getattr(event, "stop_reason", None)
        stop_type = getattr(stop_reason, "type", None)
        # end_turn and retries_exhausted are both terminal. A missing
        # stop_reason is treated as terminal so the run can never hang.
        return stop_type != BLOCKED_ON_CLIENT

    return False


def describe(event) -> str | None:
    """A one-line render of the events worth narrating during a live demo.

    Returns None for events that shouldn't be printed.
    """
    event_type = getattr(event, "type", None)

    if event_type == "session.thread_created":
        return f"  [on the bridge]    {getattr(event, 'agent_name', '?')}"
    if event_type == "session.thread_status_running":
        return f"  [investigating]    {getattr(event, 'agent_name', '?')}"
    if event_type == "agent.thread_message_sent":
        return f"  [tasked ->]        {getattr(event, 'to_agent_name', '?')}"
    if event_type == "agent.thread_message_received":
        return f"  [reported <-]      {getattr(event, 'from_agent_name', '?')}"
    if event_type == "agent.tool_use":
        return f"  [tool: {getattr(event, 'name', '?')}]"

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_events.py -v`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add swarm/events.py tests/test_events.py
git commit -m "feat: add correct session terminal gate and war-room event narration"
```

---

### Task 4: Context assembly

**Files:**
- Create: `swarm/context.py`
- Test: `tests/test_context.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_context.py`:

```python
import pytest

from swarm.context import MissingDocumentError, build_context


def test_single_document(tmp_path):
    doc = tmp_path / "incident.md"
    doc.write_text("INCIDENT BODY")
    assert build_context([doc]) == "=====  DOCUMENT: incident.md  =====\nINCIDENT BODY"


def test_multiple_documents_are_separated(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.json"
    a.write_text("AAA")
    b.write_text("BBB")
    assert build_context([a, b]) == (
        "=====  DOCUMENT: a.md  =====\nAAA\n\n"
        "=====  DOCUMENT: b.json  =====\nBBB"
    )


def test_missing_required_document_raises(tmp_path):
    with pytest.raises(MissingDocumentError) as exc:
        build_context([tmp_path / "nope.md"])
    assert "nope.md" in str(exc.value)


def test_missing_optional_document_is_skipped(tmp_path):
    present = tmp_path / "present.md"
    present.write_text("HERE")
    assert build_context([present], optional=[tmp_path / "absent.md"]) == (
        "=====  DOCUMENT: present.md  =====\nHERE"
    )


def test_present_optional_document_is_included(tmp_path):
    required = tmp_path / "r.md"
    optional = tmp_path / "o.md"
    required.write_text("R")
    optional.write_text("O")
    result = build_context([required], optional=[optional])
    assert "DOCUMENT: o.md" in result
    assert result.endswith("O")


def test_empty_input_raises(tmp_path):
    with pytest.raises(ValueError):
        build_context([])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'swarm.context'`

- [ ] **Step 3: Write the implementation**

Create `swarm/context.py`:

```python
"""Assemble the synthetic incident documents into one prompt block.

At workshop scale, inlining the ticket and supporting files into the kickoff
message is simpler than the Files API and keeps the run inspectable in one
place. The incident ticket is required; the supporting files are optional so
a team can delete one and still get a run.
"""

from pathlib import Path
from typing import Iterable, Sequence


class MissingDocumentError(FileNotFoundError):
    """A required source document was not found on disk."""


def _render(path: Path) -> str:
    return f"=====  DOCUMENT: {path.name}  =====\n{path.read_text()}"


def build_context(
    required: Sequence[Path],
    optional: Iterable[Path] = (),
) -> str:
    """Render documents into a single delimited prompt block."""
    if not required:
        raise ValueError("build_context needs at least one required document")

    blocks = []
    for path in required:
        if not path.exists():
            raise MissingDocumentError(f"Required document not found: {path}")
        blocks.append(_render(path))

    for path in optional:
        if path.exists():
            blocks.append(_render(path))

    return "\n\n".join(blocks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add swarm/context.py tests/test_context.py
git commit -m "feat: add document context assembly with required/optional split"
```

---

### Task 5: Create-once ID store (D8)

**Files:**
- Create: `swarm/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_store.py`:

```python
import json

from swarm.store import IdStore


def test_get_returns_none_when_absent(tmp_path):
    assert IdStore(tmp_path / ".swarm_ids.json").get("environment") is None


def test_set_then_get_roundtrips(tmp_path):
    store = IdStore(tmp_path / ".swarm_ids.json")
    store.set("environment", "env_abc")
    assert store.get("environment") == "env_abc"


def test_set_persists_to_disk(tmp_path):
    path = tmp_path / ".swarm_ids.json"
    IdStore(path).set("coordinator", "agent_xyz")
    assert json.loads(path.read_text()) == {"coordinator": "agent_xyz"}


def test_reload_from_disk(tmp_path):
    path = tmp_path / ".swarm_ids.json"
    IdStore(path).set("coordinator", "agent_xyz")
    assert IdStore(path).get("coordinator") == "agent_xyz"


def test_get_or_create_calls_factory_once(tmp_path):
    store = IdStore(tmp_path / ".swarm_ids.json")
    calls = []

    def factory():
        calls.append(1)
        return "agent_new"

    first, created_first = store.get_or_create("sre", factory)
    second, created_second = store.get_or_create("sre", factory)

    assert first == second == "agent_new"
    assert created_first is True
    assert created_second is False
    assert len(calls) == 1


def test_nested_namespace(tmp_path):
    store = IdStore(tmp_path / ".swarm_ids.json")
    store.set("specialists.sre", "agent_s")
    store.set("specialists.security", "agent_x")
    assert store.get("specialists.sre") == "agent_s"
    assert store.get("specialists") == {"sre": "agent_s", "security": "agent_x"}


def test_corrupt_file_raises_with_path_in_message(tmp_path):
    path = tmp_path / ".swarm_ids.json"
    path.write_text("{not json")
    try:
        IdStore(path).get("anything")
    except ValueError as exc:
        assert ".swarm_ids.json" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'swarm.store'`

- [ ] **Step 3: Write the implementation**

Create `swarm/store.py`:

```python
"""Create-once persistence for agent, environment, skill, and session IDs.

Managed Agents resources are persistent and versioned. Creating them fresh on
every run accumulates orphans and defeats version pinning, so every setup step
routes through here: look up first, create only on a miss.
"""

import json
from pathlib import Path
from typing import Any, Callable

DEFAULT_PATH = Path(".swarm_ids.json")


class IdStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{self.path} is not valid JSON ({exc}). Delete it to start over."
            ) from exc

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def get(self, key: str) -> Any:
        """Read a value. Dotted keys index into nested dicts."""
        node: Any = self._load()
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """Write a value. Dotted keys create intermediate dicts."""
        data = self._load()
        parts = key.split(".")
        node = data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        self._save(data)

    def get_or_create(self, key: str, factory: Callable[[], Any]) -> tuple[Any, bool]:
        """Return (value, created). Calls `factory` only when the key is absent."""
        existing = self.get(key)
        if existing is not None:
            return existing, False
        value = factory()
        self.set(key, value)
        return value, True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add swarm/store.py tests/test_store.py
git commit -m "feat: add create-once ID store to stop duplicate agent creation"
```

---

### Task 6: War-room roster (D3, G7)

This is the only scenario-specific module, and where the docx skill lands.

**Files:**
- Create: `swarm/roster.py`
- Test: `tests/test_roster.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_roster.py`:

```python
import pytest

from swarm import models
from swarm.roster import (
    AGENT_TOOLSET,
    POSTMORTEM_SECTIONS,
    SKILL_TO_SPECIALIST,
    SPECIALISTS,
    commander_spec,
    reviewer_spec,
)


def test_three_specialists():
    assert [s.key for s in SPECIALISTS] == ["sre", "security", "comms"]


def test_all_specialists_use_sonnet_5():
    for spec in SPECIALISTS:
        assert spec.model == models.SPECIALIST, spec.key


def test_every_specialist_has_a_system_prompt():
    for spec in SPECIALISTS:
        assert len(spec.system) > 100, spec.key


def test_every_specialist_gets_the_agent_toolset():
    for spec in SPECIALISTS:
        assert spec.tools == [{"type": AGENT_TOOLSET}]


def test_every_specialist_has_a_skill():
    """G7: no unexplained gaps — the Deal Desk build left one specialist bare."""
    assert set(SKILL_TO_SPECIALIST.values()) == {s.key for s in SPECIALISTS}


def test_skill_map_names_the_three_skill_directories():
    assert SKILL_TO_SPECIALIST == {
        "severity-runbook": "sre",
        "threat-triage": "security",
        "status-page-voice": "comms",
    }


def test_commander_uses_opus_4_8():
    assert commander_spec(["agent_a"])["model"] == models.COMMANDER


def test_commander_has_the_docx_skill():
    """Without this the postmortem document cannot be produced at all."""
    assert {"type": "anthropic", "skill_id": "docx"} in commander_spec(["agent_a"])["skills"]


def test_commander_roster_is_a_coordinator_multiagent_block():
    assert commander_spec(["agent_a", "agent_b"])["multiagent"] == {
        "type": "coordinator",
        "agents": ["agent_a", "agent_b"],
    }


def test_commander_rejects_an_empty_roster():
    with pytest.raises(ValueError):
        commander_spec([])


def test_commander_prompt_demands_parallel_fan_out():
    assert "parallel" in commander_spec(["agent_a"])["system"].lower()


def test_commander_prompt_names_the_output_path():
    assert "/mnt/session/outputs/postmortem-INC-4417.docx" in commander_spec(["a"])["system"]


def test_commander_prompt_lists_every_postmortem_section():
    system = commander_spec(["agent_a"])["system"]
    for section in POSTMORTEM_SECTIONS:
        assert section in system, section


def test_commander_prompt_requires_blameless_framing():
    assert "blameless" in commander_spec(["agent_a"])["system"].lower()


def test_commander_prompt_requires_reconciling_conflicting_findings():
    """The scenario has two candidate causes; relay is not synthesis."""
    assert "reconcile" in commander_spec(["agent_a"])["system"].lower()


def test_reviewer_uses_opus_4_8():
    assert reviewer_spec()["model"] == models.REVIEWER


def test_reviewer_prompt_demands_a_verdict():
    assert "VERDICT" in reviewer_spec()["system"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_roster.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'swarm.roster'`

- [ ] **Step 3: Write the implementation**

Create `swarm/roster.py`:

```python
"""Agent specifications for the Incident War-Room.

Pure data plus builders — nothing here touches the network, so the whole
roster (models, skills, prompts, multiagent block) is unit-testable.

This is the only scenario-specific module in `swarm/`. Changing the war-room
to another scenario means rewriting this file, `skills/`, and `synthetic-data/`
— models.py, store.py, events.py and context.py stay as they are.
"""

from dataclasses import dataclass, field
from typing import Any

from swarm import models

AGENT_TOOLSET = "agent_toolset_20260401"

METADATA = {
    "hackathon": "partner-basecamp-2026",
    "track": "incident-war-room",
}

POSTMORTEM_SECTIONS = [
    "Incident summary",
    "Timeline",
    "Root cause",
    "Was this an attack?",
    "Customer communications issued",
    "Contributing factors",
    "Action items",
]


@dataclass(frozen=True)
class SpecialistSpec:
    key: str
    name: str
    model: str
    system: str
    tools: list[dict] = field(default_factory=lambda: [{"type": AGENT_TOOLSET}])

    def to_create_kwargs(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "system": self.system,
            "tools": self.tools,
            "metadata": {**METADATA, "role": self.key},
        }


SPECIALISTS: list[SpecialistSpec] = [
    SpecialistSpec(
        key="sre",
        name="SRE Responder",
        model=models.SPECIALIST,
        system=(
            "You are the SRE Responder on an active incident bridge. The site "
            "is degraded right now. Your job is root cause and mitigation.\n\n"
            "Inputs you'll receive:\n"
            "- The incident ticket (alerts, error rates, affected services)\n"
            "- service-topology.md (what depends on what)\n"
            "- recent-changes.json (every deploy and config change in the last 24h)\n"
            "- The severity-runbook skill (your authoritative severity matrix, "
            "SLO burn thresholds, known failure modes, and rollback criteria)\n\n"
            "Your output, in one message, ~300 words:\n"
            "1. Severity classification, per the runbook — state which criterion you matched\n"
            "2. Your leading root-cause hypothesis, and your confidence in it\n"
            "3. The evidence for it, and the evidence AGAINST it\n"
            "4. Immediate mitigation — and an explicit rollback yes/no with reasoning\n"
            "5. What you'd need to confirm the hypothesis\n\n"
            "Be honest about uncertainty. If the evidence supports more than one "
            "cause, say so — the Incident Commander is reconciling your findings "
            "with the Security Analyst's and needs to know what you are not sure of. "
            "Do not speculate about malicious activity; that is Security's lane."
        ),
    ),
    SpecialistSpec(
        key="security",
        name="Security Analyst",
        model=models.SPECIALIST,
        system=(
            "You are the Security Analyst on an active incident bridge. Your job "
            "is to answer one question first — is this an attack or a failure? — "
            "and then scope the blast radius.\n\n"
            "Inputs you'll receive:\n"
            "- The incident ticket (including raw alert payloads and traffic data)\n"
            "- service-topology.md (for blast-radius tracing)\n"
            "- The threat-triage skill (your attack-vs-failure decision tree, "
            "blast-radius method, IOC checklist, and disclosure triggers)\n\n"
            "Your output, in one message, ~300 words:\n"
            "1. VERDICT: ATTACK / NOT AN ATTACK / INCONCLUSIVE — lead with this\n"
            "2. The decision-tree path that got you there\n"
            "3. Blast radius: which systems and what data could have been reached\n"
            "4. Whether any disclosure trigger from the skill has been met\n"
            "5. Containment actions you recommend, if any\n\n"
            "INCONCLUSIVE is a legitimate verdict — say it rather than guessing. "
            "If an anomaly has a plausible benign explanation, name it. The "
            "Incident Commander is reconciling your findings with the SRE's, so "
            "flag explicitly where your evidence and theirs might describe the "
            "same event."
        ),
    ),
    SpecialistSpec(
        key="comms",
        name="Comms Lead",
        model=models.SPECIALIST,
        system=(
            "You are the Comms Lead on an active incident bridge. You draft what "
            "customers see. Your draft may be published close to verbatim, so "
            "write it that way.\n\n"
            "Inputs you'll receive:\n"
            "- The incident ticket\n"
            "- The status-page-voice skill (your template, tone rules, and the "
            "rules on what may and may not be claimed before root cause is "
            "confirmed)\n\n"
            "Your output, in one message:\n"
            "1. A status-page update, ready to publish, following the skill's template\n"
            "2. A one-line internal note on what you deliberately did NOT say, and why\n"
            "3. The next update time you're committing to\n\n"
            "Hard rules: do not state a root cause that has not been confirmed. Do "
            "not speculate about security. Do not promise a restoration time you "
            "cannot support. Do not blame a vendor. If the incident is still "
            "unresolved, the update should say so plainly — customers tolerate "
            "'we don't know yet' far better than a claim that turns out to be wrong."
        ),
    ),
]


# Skill directory name -> specialist key. Every specialist has one (PRD G7).
SKILL_TO_SPECIALIST = {
    "severity-runbook": "sre",
    "threat-triage": "security",
    "status-page-voice": "comms",
}


COMMANDER_SYSTEM = """\
You are the Incident Commander. INC-4417 is active and customers are affected.
You run the bridge: task the specialists, reconcile what they bring back, and
write the postmortem.

# Your roster

- SRE Responder: root cause, mitigation, rollback call
- Security Analyst: attack-or-failure verdict, blast radius, disclosure triggers
- Comms Lead: customer-facing status update

# How to run the bridge

1. Read the incident ticket yourself first. Note severity, what's affected, and
   when it started.

2. Task ALL THREE specialists in parallel. Do not wait for one before starting
   the next — this is an active incident. Each gets:
   - The full incident ticket
   - A narrow brief stating exactly what you need from them
   - A deadline ("one message, ~300 words")

3. Reconcile their findings. This is the part that matters. The specialists see
   different evidence and may reach conclusions that appear to conflict. Two
   findings that look contradictory are often the same event seen from two
   angles. Work out which of these you are looking at:
   - Two independent causes that coincided
   - One cause that both specialists detected differently
   - One real cause plus one coincidental anomaly
   State which, and say what evidence settles it. If the evidence does not
   settle it, say that explicitly and list what would.

4. Write the postmortem as a Word document using the docx skill, saved to
   /mnt/session/outputs/postmortem-INC-4417.docx. Sections, in order:

   1. Incident summary — severity, duration, customer impact
   2. Timeline
   3. Root cause
   4. Was this an attack?
   5. Customer communications issued
   6. Contributing factors
   7. Action items — each with an owner role and a priority

   The deliverable is the .docx file, not a chat message. Do not end your turn
   until that file exists.

# Postmortem standards

Blameless. Describe what the system allowed to happen, never who made a
mistake. "The deploy pipeline permitted a config change without a staged
rollout" — not "an engineer skipped staging." Name roles, never individuals.

Action items must be specific and testable. "Add a canary stage to the config
deploy pipeline" is an action item. "Improve deployment safety" is not.

If a question remains genuinely open, write it down as open. A postmortem that
overstates certainty is worse than one that admits a gap.

# Tone

Incident commander running a live bridge. Calm, terse, decisive. You are moving
fast because customers are affected right now.
"""


def commander_spec(roster: list[str]) -> dict[str, Any]:
    """Build the Incident Commander's `agents.create()` kwargs.

    `roster` is a list of specialist agent IDs the commander may delegate to.
    """
    if not roster:
        raise ValueError("The commander needs at least one specialist in its roster")

    return {
        "name": "Incident Commander",
        "model": models.COMMANDER,
        "system": COMMANDER_SYSTEM,
        "tools": [{"type": AGENT_TOOLSET}],
        # The docx skill is what turns the synthesis into the deliverable.
        "skills": [{"type": "anthropic", "skill_id": "docx"}],
        "multiagent": {"type": "coordinator", "agents": list(roster)},
        "metadata": {**METADATA, "role": "commander"},
    }


REVIEWER_SYSTEM = """\
You are the Postmortem Reviewer. You don't run incidents. You decide whether a
postmortem is fit to publish.

When the Incident Commander sends you a draft, you'll receive:
- The draft postmortem
- The incident ticket (for context)

Deliver one of three verdicts.

1. **PUBLISH** — the postmortem is sound, with at most cosmetic suggestions.
2. **REVISE** — specific defects that must be fixed. List them tersely, no more
   than five. If there are more than five, the draft isn't ready.
3. **ESCALATE** — this postmortem cannot be published as-is because the incident
   itself needs more attention: an unresolved security question, an unquantified
   customer impact, or a root cause that is still speculation presented as fact.

Check specifically for:
- Blame. Any individual named, or any phrasing that implies personal fault.
- Overstated certainty. A root cause asserted where the evidence was inconclusive.
- Unreconciled findings. If SRE and Security disagreed and the draft just
  reports both without resolving or explicitly flagging the conflict, that is a
  REVISE.
- Vague action items. Anything not specific enough to be verifiably done.
- Missing sections.

Be sceptical. Your value is that you push back. A commander who never gets
pushback publishes postmortems that teach nobody anything.

Lead your reply with: VERDICT: PUBLISH / REVISE / ESCALATE.
"""


def reviewer_spec() -> dict[str, Any]:
    """Build the stretch-goal postmortem reviewer's `agents.create()` kwargs."""
    return {
        "name": "Postmortem Reviewer",
        "model": models.REVIEWER,
        "system": REVIEWER_SYSTEM,
        "tools": [{"type": AGENT_TOOLSET}],
        "metadata": {**METADATA, "role": "reviewer"},
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_roster.py -v`
Expected: PASS, 17 tests.

- [ ] **Step 5: Commit**

```bash
git add swarm/roster.py tests/test_roster.py
git commit -m "feat: add incident war-room roster with docx skill on the commander"
```

---

### Task 7: Author the three specialist skills

Skills carry the domain truth that makes specialist output grounded rather than invented. Each needs YAML frontmatter with `name` and `description` — the description is what the model uses to decide relevance, so it must state the trigger.

**Files:**
- Create: `skills/severity-runbook/SKILL.md`
- Create: `skills/threat-triage/SKILL.md`
- Create: `skills/status-page-voice/SKILL.md`
- Delete: `skills/pricing-playbook/`, `skills/legal-checklist/`, `skills/competitive-intel/`

- [ ] **Step 1: Remove the Deal Desk skills**

```bash
rm -rf skills/pricing-playbook skills/legal-checklist skills/competitive-intel
```

- [ ] **Step 2: Create the SRE skill**

Create `skills/severity-runbook/SKILL.md`:

```markdown
---
name: severity-runbook
description: BTS-Synthetic production severity matrix, SLO burn thresholds, known failure modes and rollback criteria. Use whenever classifying an incident's severity, forming a root-cause hypothesis, or deciding whether to roll back. Trigger on any request to triage, diagnose, classify, or mitigate a production incident.
---

# Production Severity Runbook

## Severity matrix

Classify by customer impact, not by how alarming the graph looks.

| Sev | Criterion (any one matches) | Response |
| --- | --- | --- |
| SEV1 | Total outage of a revenue path, OR confirmed data loss, OR >25% of requests failing globally | Page exec on-call. Bridge within 5 min. Status page immediately. |
| SEV2 | A revenue path degraded for a subset of users, OR 5–25% error rate, OR a hard dependency down with degraded fallback | Page service owner. Bridge within 15 min. Status page within 30 min. |
| SEV3 | Single non-critical service degraded, no revenue impact, fallback holding | Ticket. Business hours. No status page. |
| SEV4 | Cosmetic, internal-only, or fully absorbed by redundancy | Ticket. Next sprint. |

**Checkout is a revenue path.** Any confirmed checkout failure is SEV2 minimum,
regardless of the percentage affected.

## SLO burn thresholds

Checkout API SLO: 99.9% success, 30-day window. Error budget = 43.2 min/month.

| Burn rate | Meaning | Action |
| --- | --- | --- |
| >14.4x | Budget exhausted in <2 days | Page. Treat as SEV1/SEV2. |
| 6x–14.4x | Budget exhausted in 2–5 days | Page. SEV2. |
| 1x–6x | Elevated, budget survives the window | Ticket, monitor |
| <1x | Within budget | No action |

## Known failure modes

Check these before hypothesising anything novel. In order of historical frequency:

1. **Config change without staged rollout.** Our config deploys are not canaried.
   A bad value reaches all regions in one push. Signature: onset is sharp, error
   rate steps rather than ramps, and onset correlates within ~60 min of a
   config-type entry in the change log.
2. **Connection pool exhaustion under retry storm.** A downstream slowdown causes
   client retries, which exhaust the pool, which causes more failures. Signature:
   latency climbs *before* errors, and the error rate is self-sustaining after
   the original trigger clears.
3. **Certificate or credential expiry.** Signature: total, instant, and
   region-uniform. If failures are partial or regional, this is not it.
4. **Regional dependency failure.** Signature: error rate correlates precisely
   with a region boundary and no change was deployed.
5. **Traffic-shape change exceeding capacity.** Signature: gradual ramp, no
   deploy correlation, request volume elevated above the trailing baseline.

## Rollback criteria

Roll back when **all three** hold:

- A change was deployed within 2 hours before onset
- The change touches the failing path
- Rollback is safe — no schema migration, no irreversible data write since deploy

Roll back **immediately without waiting for root cause** if it is SEV1. Diagnosis
is cheaper after the bleeding stops.

Do **not** roll back when:
- The change predates onset by more than 2 hours with no plausible latency
- Rollback would itself cause data inconsistency
- Error rate is already recovering on its own

## Hypothesis discipline

State confidence explicitly, and state disconfirming evidence. A correlated
deploy is evidence, not proof — two things can change in the same window. If a
second signal (traffic anomaly, dependency alert) is present in the same window,
say so rather than dismissing it; someone else on the bridge may be looking at
the other half of the same event.
```

- [ ] **Step 3: Create the Security skill**

Create `skills/threat-triage/SKILL.md`:

```markdown
---
name: threat-triage
description: BTS-Synthetic security incident triage — attack-versus-failure decision tree, blast-radius method, indicator checklist, and regulatory disclosure triggers. Use whenever assessing whether a production incident involves malicious activity, scoping what an attacker could have reached, or deciding whether disclosure obligations are triggered.
---

# Security Incident Triage

## Attack vs. failure decision tree

Work top down. Stop at the first node that resolves.

1. **Is there a plausible non-malicious cause with matching timing?**
   A deploy, config change, cert expiry, or dependency failure in the window.
   → If yes, and it explains the *full* symptom set, verdict is NOT AN ATTACK.
   → If it explains only part, continue. Partial explanation is the most
     commonly missed case: a real failure and a real probe can coincide.

2. **Is the anomalous traffic distinguishable from legitimate traffic?**
   Check: source concentration (single ASN, single /24, single UA string),
   request shape (identical paths, unusual parameter patterns, absent referrers),
   and timing (machine-regular intervals).
   → Concentrated + machine-regular + unusual shape → continue to 3.
   → Diffuse, human-irregular, normal shape → likely legitimate. Note it and
     move on.

3. **Is the traffic targeting something valuable, or just present?**
   Scanning for `/wp-admin` on a service that has never had WordPress is noise.
   Repeated auth attempts, parameter fuzzing on a payment path, or enumeration
   of valid identifiers is not.
   → Targeting a valuable path → continue to 4.
   → Untargeted background noise → NOT AN ATTACK, note as background.

4. **Did it succeed at anything?**
   Any 2xx on an attack-shaped request. Any auth success from the anomalous
   source. Any data-volume anomaly on the response side.
   → Yes → ATTACK, and treat as confirmed compromise until disproven.
   → No, but the attempt is clear and targeted → ATTACK (attempted).
   → Cannot determine from available telemetry → INCONCLUSIVE.

**INCONCLUSIVE is a legitimate verdict.** Use it when telemetry cannot settle
the question. Do not resolve ambiguity by guessing in either direction — an
overstated ATTACK triggers costly response, an overstated NOT AN ATTACK ends
the investigation early.

## The coincidence rule

An anomalous traffic pattern in the same window as a deploy does **not** make
the deploy innocent, and does not make the traffic guilty. Both can be real and
unrelated. Explicitly consider three cases and say which you believe:

| Case | What it looks like |
| --- | --- |
| Traffic caused the failure | Failure onset follows traffic onset; failure scales with traffic volume |
| Failure attracted the traffic | Traffic onset follows failure onset (scanners find error pages) |
| Unrelated coincidence | Onsets are independent; failure symptom is fully explained by the change |

## Blast radius method

Trace outward from the affected service in `service-topology.md`:

1. **Direct reach** — what the affected service can call, and with what credentials
2. **Data reach** — what data stores those credentials can read or write
3. **Lateral reach** — what else shares those credentials or that network segment
4. **Trust reach** — what downstream systems accept output from this service without revalidation

Report reach as *what was possible*, and separately *what telemetry shows was
actually accessed*. Do not conflate them.

## Indicator checklist

- [ ] Source ASN / IP concentration
- [ ] User-agent anomalies or absence
- [ ] Request-rate regularity (machine vs human distribution)
- [ ] Auth failure spike, and any auth success from the anomalous source
- [ ] Response-size anomalies (exfiltration signature)
- [ ] Requests to paths that have never legitimately existed
- [ ] Timing relative to the change log

## Disclosure triggers

Escalate to Legal and Privacy **immediately** if any hold:

| Trigger | Obligation |
| --- | --- |
| Personal data confirmed accessed by an unauthorised party | GDPR Art. 33 — 72h regulator notification |
| Payment card data in the blast radius, access not excluded | PCI DSS incident response, acquirer notification |
| Authentication credentials exposed | Forced rotation + user notification |
| Confirmed unauthorised access to any production data store | Legal review for contractual notification duties |

"Access not excluded" is the trigger, not "access confirmed." If you cannot rule
it out, escalate — the clock starts at awareness, not at proof.
```

- [ ] **Step 4: Create the Comms skill**

Create `skills/status-page-voice/SKILL.md`:

```markdown
---
name: status-page-voice
description: BTS-Synthetic customer-facing incident communication standards — status page template, tone rules, and the rules on what may and may not be claimed before root cause is confirmed. Use whenever drafting a status page update, customer incident notification, or any external message during an active incident.
---

# Status Page Voice

## Template

Every update uses this shape. Do not improvise structure mid-incident.

```
**[STATUS] — [Component]**
[Timestamp UTC]

[What customers are experiencing — one sentence, plain language.]

[What we are doing — one or two sentences, present tense.]

[What customers should do, if anything. Omit this line if the answer is nothing.]

Next update: [time or interval].
```

Status values, in order of progression: **Investigating → Identified →
Monitoring → Resolved**. Never skip backwards without explanation. Never post
Resolved until recovery has held for at least 30 minutes.

## What you may and may not say

| Before root cause is confirmed | |
| --- | --- |
| ✅ "A subset of customers are experiencing errors at checkout." | Observable symptom |
| ✅ "We have identified a likely cause and are testing a fix." | Progress without a claim |
| ✅ "We do not yet know the cause." | Honest, and better than a wrong guess |
| ❌ "This was caused by a configuration change." | Unconfirmed attribution |
| ❌ "This is not a security incident." | Never claim this before Security has a verdict |
| ❌ "No customer data was affected." | An assertion you may have to retract |
| ❌ "Service will be restored within the hour." | A promise you cannot support |
| ❌ "A third-party provider is experiencing issues." | Never name or blame a vendor externally |

**The retraction rule.** The cost of saying "we don't know yet" is mild customer
frustration. The cost of retracting a confident claim is trust you do not get
back. When in doubt, say less.

## Tone rules

- **Plain language.** "Customers may see errors when completing a purchase" —
  not "the checkout service is returning elevated 5xx responses."
- **Active voice, first person plural.** "We are investigating." Not "the issue
  is being investigated."
- **No hedging stacks.** "We believe it may be possible that" is one sentence
  saying nothing. Pick a confidence level and state it once.
- **No apologising in every paragraph.** Once, sincerely, at Resolved. Repeated
  apologies read as panic.
- **No internal vocabulary.** No service names, no severity levels, no runbook
  terms, no incident IDs customers cannot use.
- **No emoji. No exclamation marks.**

## Cadence

| Severity | Update interval | First update due |
| --- | --- | --- |
| SEV1 | Every 30 min, without fail | Within 15 min of detection |
| SEV2 | Every 60 min | Within 30 min of detection |
| SEV3+ | No status page unless customers ask | — |

Post the update even when there is nothing new. "We are still investigating and
have no further update. Next update at 14:30 UTC." Silence reads as absence.

**Commit to a next-update time in every post, and meet it.** A missed committed
update is worse than a longer stated interval.

## Resolved posts

At Resolved, state: what happened in one plain sentence, when it started and
ended, who was affected, and whether a fuller writeup will follow. Do not
publish root-cause detail at Resolved unless it is confirmed — that is what the
postmortem is for.
```

- [ ] **Step 5: Verify frontmatter parses on all three**

Run:
```bash
for f in skills/*/SKILL.md; do
  echo "--- $f"
  head -4 "$f" | grep -E "^(name|description):" | cut -c1-60
done
```
Expected: each file shows a `name:` and a `description:` line. Three files listed.

- [ ] **Step 6: Verify skill directory names match the roster map**

Run:
```bash
python -c "
from pathlib import Path
from swarm.roster import SKILL_TO_SPECIALIST
on_disk = {p.name for p in Path('skills').iterdir() if p.is_dir()}
assert on_disk == set(SKILL_TO_SPECIALIST), (on_disk, set(SKILL_TO_SPECIALIST))
print('skills match roster:', sorted(on_disk))
"
```
Expected: `skills match roster: ['severity-runbook', 'status-page-voice', 'threat-triage']`

- [ ] **Step 7: Commit**

```bash
git add skills/
git commit -m "feat: author SRE, security and comms incident skills"
```

---

### Task 8: Author the synthetic incident data

The scenario needs a deliberately ambiguous cause — a config deploy *and* a traffic anomaly in the same window — so that reconciliation is real work and relay is visibly insufficient.

**Files:**
- Create: `synthetic-data/incident-INC-4417.md`
- Create: `synthetic-data/service-topology.md`
- Create: `synthetic-data/recent-changes.json`
- Create: `synthetic-data/past-incidents.json`
- Delete: `synthetic-data/rfp-acme-corp.md`, `past-wins.json`, `product-overview.md`

- [ ] **Step 1: Remove the Deal Desk data**

```bash
rm -f synthetic-data/rfp-acme-corp.md synthetic-data/past-wins.json synthetic-data/product-overview.md
```

- [ ] **Step 2: Create the incident ticket**

Create `synthetic-data/incident-INC-4417.md`:

```markdown
# INC-4417 — Checkout API elevated 5xx, EU + APAC

**Status:** ACTIVE
**Declared:** 2026-07-21 13:42 UTC
**Detected by:** Automated alert — `checkout-api-error-rate` (Datadog monitor #8821)
**Current severity:** SEV2 (provisional — pending on-bridge classification)
**Incident channel:** #inc-4417
**Bridge opened:** 2026-07-21 13:51 UTC

## On-call acknowledgements

| Time (UTC) | Who | Note |
| --- | --- | --- |
| 13:42 | Auto-page → platform-oncall | — |
| 13:47 | platform-oncall ack | "Looking. Error rate climbing." |
| 13:51 | Bridge opened, IC assigned | — |
| 13:58 | security-oncall joined | "Saw the traffic alert, joining." |

## Symptoms

Checkout API returning HTTP 502 and 503 for a subset of requests. Customers
see "Something went wrong, please try again" at the payment step. Retry
sometimes succeeds.

### Error rate — `checkout-api`, 5-minute buckets

| Time (UTC) | Requests | 5xx | Error rate |
| --- | --- | --- | --- |
| 12:30 | 41,203 | 12 | 0.03% |
| 12:45 | 40,880 | 9 | 0.02% |
| 13:00 | 42,110 | 14 | 0.03% |
| 13:15 | 41,660 | 31 | 0.07% |
| 13:30 | 43,020 | 402 | 0.93% |
| 13:35 | 44,190 | 3,981 | 9.01% |
| 13:40 | 44,720 | 5,102 | 11.41% |
| 13:45 | 45,330 | 5,644 | 12.45% |
| 14:00 | 45,900 | 5,808 | 12.65% |
| 14:15 | 46,120 | 5,891 | 12.77% |

Onset is sharp between 13:15 and 13:35. Error rate has plateaued, not recovered.

### Affected regions

| Region | Error rate | Note |
| --- | --- | --- |
| eu-west-1 | 21.4% | Worst affected |
| ap-southeast-1 | 18.9% | |
| us-east-1 | 0.04% | Baseline — unaffected |
| us-west-2 | 0.03% | Baseline — unaffected |

### Latency

p50 unchanged at 82ms. p99 up from 340ms to 1,180ms in affected regions only.
Latency rise begins ~13:20, roughly 10 minutes before the error-rate step.

## Raw alert payloads

```json
[
  {
    "monitor": "checkout-api-error-rate",
    "id": 8821,
    "triggered_at": "2026-07-21T13:42:11Z",
    "threshold": "error_rate > 1% over 5m",
    "value": 0.0901,
    "scope": "service:checkout-api",
    "message": "Checkout API 5xx above threshold"
  },
  {
    "monitor": "payment-gateway-connection-pool",
    "id": 8834,
    "triggered_at": "2026-07-21T13:37:48Z",
    "threshold": "pool_available < 5 over 5m",
    "value": 0,
    "scope": "service:checkout-api,region:eu-west-1",
    "message": "Connection pool to payment-gateway exhausted"
  },
  {
    "monitor": "waf-anomalous-source-volume",
    "id": 9102,
    "triggered_at": "2026-07-21T13:19:30Z",
    "threshold": "single_asn_request_share > 15% over 10m",
    "value": 0.231,
    "scope": "edge:global",
    "message": "23.1% of edge traffic from AS-204889 (baseline 0.4%)"
  }
]
```

## Edge traffic detail (from WAF alert 9102)

Between 13:19 and 14:15, AS-204889 accounted for 23.1% of edge requests, up
from a 0.4% trailing baseline.

| Property | Value |
| --- | --- |
| Source ASN | AS-204889 |
| Distinct source IPs | 1,847 across 6 /24 ranges |
| Target paths | `/api/v2/checkout/session` (94%), `/api/v2/checkout/quote` (6%) |
| User-agent | `okhttp/4.9.3` on 100% of requests |
| Request interval | Median 1.02s, standard deviation 0.04s |
| HTTP status distribution | 502: 61%, 503: 22%, 200: 17% |
| Response size on 200s | Median 1.4 KB — matches normal quote response |
| Auth | 100% unauthenticated; all requests hit the pre-auth quote path |
| Geography | Registered to a mobile carrier, ap-southeast region |

No authentication attempts. No requests to paths outside the two above. No
parameter variation beyond normal quote fields.

## What we know

- The error rate stepped sharply between 13:15 and 13:35 and has plateaued
- Only eu-west-1 and ap-southeast-1 are affected; US regions are clean
- Connection pool to `payment-gateway` is exhausted in eu-west-1
- Latency began rising ~10 minutes before errors
- Anomalous single-ASN traffic began at ~13:19
- A change was deployed at 13:04 (see `recent-changes.json`)

## What we do not know

- Whether the deploy, the traffic, or both caused this
- Whether the AS-204889 traffic is an attack, a misbehaving mobile client, or a
  partner integration nobody documented
- Why US regions are unaffected
- Whether any customer completed a payment that was charged but not recorded
```

- [ ] **Step 3: Create the service topology**

Create `synthetic-data/service-topology.md`:

```markdown
# Service Topology — Checkout Path

## Dependency chain

```
edge-cdn  →  api-gateway  →  checkout-api  →  payment-gateway  →  [external PSP]
                                  │
                                  ├──→  inventory-svc        (hard dependency)
                                  ├──→  pricing-svc          (hard dependency)
                                  ├──→  session-store        (Redis, hard)
                                  └──→  order-db             (Postgres, hard)
```

## Services

| Service | Owner role | Criticality | Notes |
| --- | --- | --- | --- |
| `edge-cdn` | Platform | SEV1 path | WAF runs here. Global anycast. |
| `api-gateway` | Platform | SEV1 path | Auth termination. Rate limiting configured here. |
| `checkout-api` | Payments | SEV1 path | The affected service. Stateless, autoscaled. |
| `payment-gateway` | Payments | SEV1 path | Connection-pooled. **Pool size is a config value, not autoscaled.** |
| `inventory-svc` | Fulfilment | SEV2 | Degrades to "assume in stock" on failure |
| `pricing-svc` | Commerce | SEV2 | Degrades to cached price on failure |
| `session-store` | Platform | SEV1 path | Redis cluster, per-region |
| `order-db` | Payments | SEV1 path | Postgres, primary in us-east-1, read replicas per region |

## Regional deployment

| Region | checkout-api | payment-gateway | session-store |
| --- | --- | --- | --- |
| us-east-1 | ✅ | ✅ (pool: 200) | ✅ |
| us-west-2 | ✅ | ✅ (pool: 200) | ✅ |
| eu-west-1 | ✅ | ✅ (pool: **50**) | ✅ |
| ap-southeast-1 | ✅ | ✅ (pool: **50**) | ✅ |

Pool sizes are set per-region in `checkout-api` config. EU and APAC were sized
smaller during a 2025 cost-reduction exercise and have not been revisited.

## Credentials and trust

- `checkout-api` holds: `payment-gateway` service token, `order-db` write
  credentials, `session-store` credentials
- `payment-gateway` holds: external PSP API key (scoped to charge + refund)
- `order-db` write credentials are **shared** between `checkout-api` and
  `fulfilment-worker`
- `payment-gateway` accepts requests from `checkout-api` without revalidating
  the customer session — it trusts the caller

## Data classification

| Store | Contains | Classification |
| --- | --- | --- |
| `order-db` | Order records, billing address, last-4 of card | PII + PCI-adjacent |
| `session-store` | Session tokens, cart contents | PII |
| `payment-gateway` | No storage — pass-through to PSP | Card data transits, never persisted |

## Pre-auth surface

`/api/v2/checkout/quote` is **unauthenticated by design** — it returns a price
quote for a cart without requiring login. It is rate-limited at the gateway to
100 req/min per IP. There is no per-ASN limit.

`/api/v2/checkout/session` requires authentication and creates a session record.
```

- [ ] **Step 4: Create the change log**

Create `synthetic-data/recent-changes.json`:

```json
{
  "window": "2026-07-20T14:00:00Z to 2026-07-21T14:00:00Z",
  "changes": [
    {
      "id": "CHG-9912",
      "deployed_at": "2026-07-21T13:04:22Z",
      "service": "checkout-api",
      "type": "config",
      "summary": "Reduce payment-gateway connection pool timeout from 30s to 5s",
      "detail": "Part of latency-reduction workstream. Intent: fail fast on slow PSP responses rather than holding pool connections. Applied to all regions simultaneously.",
      "staged_rollout": false,
      "canary": false,
      "author_role": "Payments engineer",
      "reviewed_by_role": "Payments tech lead",
      "rollback_safe": true,
      "rollback_notes": "Config-only. No schema change. Revert is a single value."
    },
    {
      "id": "CHG-9908",
      "deployed_at": "2026-07-21T09:15:00Z",
      "service": "pricing-svc",
      "type": "code",
      "summary": "Add currency rounding rule for JPY",
      "staged_rollout": true,
      "canary": true,
      "author_role": "Commerce engineer",
      "rollback_safe": true
    },
    {
      "id": "CHG-9901",
      "deployed_at": "2026-07-20T16:40:00Z",
      "service": "inventory-svc",
      "type": "code",
      "summary": "Batch stock-level reads",
      "staged_rollout": true,
      "canary": true,
      "author_role": "Fulfilment engineer",
      "rollback_safe": true
    },
    {
      "id": "CHG-9897",
      "deployed_at": "2026-07-20T14:22:00Z",
      "service": "edge-cdn",
      "type": "config",
      "summary": "WAF rule update — add anomalous-source-volume monitor",
      "detail": "Added monitor 9102. Detection only, no blocking action configured.",
      "staged_rollout": false,
      "canary": false,
      "author_role": "Security engineer",
      "rollback_safe": true
    }
  ]
}
```

- [ ] **Step 5: Create the prior-incident file**

Create `synthetic-data/past-incidents.json`:

```json
{
  "incidents": [
    {
      "id": "INC-3908",
      "date": "2026-02-14",
      "severity": "SEV2",
      "title": "Checkout 5xx after connection pool config change",
      "duration_minutes": 74,
      "root_cause": "A pool-size reduction deployed without canary exhausted available connections under normal peak load in smaller regions. US regions were unaffected because their pools had headroom.",
      "resolution": "Rolled back the config change. Error rate recovered within 6 minutes.",
      "action_items_status": "2 of 3 completed. 'Add canary stage to config deploy pipeline' remains OPEN.",
      "note": "Same shape as a config-only change reaching all regions at once."
    },
    {
      "id": "INC-4102",
      "date": "2026-04-30",
      "severity": "SEV3",
      "title": "Anomalous single-ASN traffic to quote endpoint",
      "duration_minutes": 0,
      "root_cause": "A partner's mobile SDK shipped with an aggressive retry loop and no jitter. Traffic was legitimate but badly behaved. No customer impact — quote endpoint absorbed it.",
      "resolution": "Contacted partner, they shipped a fix in 9 days. Added per-ASN rate limiting to the backlog.",
      "action_items_status": "1 of 2 completed. 'Per-ASN rate limiting at gateway' remains OPEN.",
      "note": "Traffic signature was near-identical to a scraping attack. Initial verdict was ATTACK; revised after partner contact."
    },
    {
      "id": "INC-4310",
      "date": "2026-06-08",
      "severity": "SEV1",
      "title": "Total checkout outage — expired PSP certificate",
      "duration_minutes": 31,
      "root_cause": "PSP client certificate expired. No expiry monitoring existed.",
      "resolution": "Emergency certificate rotation.",
      "action_items_status": "All 3 completed. Certificate expiry monitoring now in place.",
      "note": "Failure was total, instant and region-uniform — the opposite signature to a partial regional degradation."
    }
  ]
}
```

- [ ] **Step 6: Verify the data files parse**

Run:
```bash
python -c "
import json
for f in ['synthetic-data/recent-changes.json', 'synthetic-data/past-incidents.json']:
    json.load(open(f))
    print('ok', f)
"
```
Expected:
```
ok synthetic-data/recent-changes.json
ok synthetic-data/past-incidents.json
```

- [ ] **Step 7: Commit**

```bash
git add synthetic-data/
git commit -m "feat: add synthetic INC-4417 incident with dual-cause ambiguity"
```

---

### Task 9: Rewrite `setup_environment.py` and `create_specialists.py` (D7, D8)

**Files:**
- Modify: `setup_environment.py`
- Modify: `create_specialists.py`

- [ ] **Step 1: Rewrite `setup_environment.py`**

Replace the entire file with:

```python
"""Create the cloud Environment the war-room session runs in.

Safe to re-run — the environment ID is recorded in .swarm_ids.json and reused.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python setup_environment.py
"""

import os

from anthropic import Anthropic

from swarm.store import IdStore


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    client = Anthropic()

    def create() -> str:
        environment = client.beta.environments.create(
            name="incident-war-room-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        return environment.id

    environment_id, created = store.get_or_create("environment", create)

    print(f"{'Created' if created else 'Reusing'} environment: {environment_id}")
    print("\nNext: python create_specialists.py")


if __name__ == "__main__":
    main()
```

No `default_headers` — the SDK sets `managed-agents-2026-04-01` automatically on every `client.beta.*` call (D7).

- [ ] **Step 2: Rewrite `create_specialists.py`**

Replace the entire file with:

```python
"""Create the three specialist sub-agents for the Incident War-Room.

SRE Responder, Security Analyst, Comms Lead. Each gets a narrow system prompt
and the agent toolset; upload_skills.py attaches their domain skill afterwards.

Safe to re-run — agent IDs are recorded in .swarm_ids.json and reused. Agents
are persistent, versioned resources: create once, reference by ID thereafter.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python create_specialists.py
"""

import os

from anthropic import Anthropic

from swarm.roster import SPECIALISTS
from swarm.store import IdStore


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    client = Anthropic()

    for spec in SPECIALISTS:
        def create(spec=spec) -> str:
            return client.beta.agents.create(**spec.to_create_kwargs()).id

        agent_id, created = store.get_or_create(f"specialists.{spec.key}", create)
        print(f"  {'Created ' if created else 'Reusing '} {spec.name:22s} -> {agent_id}")

    print(f"\n{len(SPECIALISTS)} specialists ready in .swarm_ids.json")
    print("Next: python upload_skills.py")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the modules import and carry no stale IDs**

Run: `python -c "import setup_environment, create_specialists; print('ok')"`
Expected: `ok`

Run: `grep -c "claude-opus-4-7\|claude-sonnet-4-6" setup_environment.py create_specialists.py`
Expected: `0` for both files.

- [ ] **Step 4: Commit**

```bash
git add setup_environment.py create_specialists.py
git commit -m "refactor: make environment and specialist setup idempotent"
```

---

### Task 10: Rewrite `upload_skills.py`

**Files:**
- Modify: `upload_skills.py`

- [ ] **Step 1: Rewrite the file**

Replace the entire file with:

```python
"""Upload each custom skill in skills/ and attach it to its specialist.

Idempotent in both directions: existing skills are matched by display title
and reused, and a skill already attached to an agent is not re-attached.

Usage:
    python upload_skills.py
"""

import os
from pathlib import Path

from anthropic import Anthropic
from anthropic.lib import files_from_dir

from swarm.roster import SKILL_TO_SPECIALIST
from swarm.store import IdStore


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    if store.get("specialists") is None:
        raise SystemExit("No specialists found. Run create_specialists.py first.")

    client = Anthropic()

    # The Skills API enforces unique display titles, so a retry with the same
    # title would 409. List first and reuse.
    print("Checking for existing skills...")
    existing_by_title = {
        s.display_title: s.id for s in client.beta.skills.list(source="custom")
    }

    for skill_name, specialist_key in SKILL_TO_SPECIALIST.items():
        skill_dir = Path("skills") / skill_name
        if not (skill_dir / "SKILL.md").exists():
            print(f"  Skipping {skill_name} — no SKILL.md found")
            continue

        display_title = skill_name.replace("-", " ").title()

        def create(skill_dir=skill_dir, display_title=display_title) -> str:
            if display_title in existing_by_title:
                return existing_by_title[display_title]
            skill = client.beta.skills.create(
                display_title=display_title,
                files=files_from_dir(str(skill_dir)),
            )
            return skill.id

        skill_id, created = store.get_or_create(f"skills.{skill_name}", create)
        print(f"{'Uploaded' if created else 'Reusing '} skill: {skill_name} ({skill_id})")

        specialist_id = store.get(f"specialists.{specialist_key}")
        if specialist_id is None:
            print(f"  ! No agent for `{specialist_key}` — skipping attach")
            continue

        agent = client.beta.agents.retrieve(specialist_id)
        current = list(agent.skills or [])
        if any(s.get("skill_id") == skill_id for s in current):
            print(f"  already attached to `{specialist_key}` ✓")
            continue

        client.beta.agents.update(
            specialist_id,
            version=agent.version,
            skills=current + [{"type": "custom", "skill_id": skill_id, "version": "latest"}],
        )
        print(f"  attached to `{specialist_key}` ✓")

    print("\nNext: python create_coordinator.py")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "import upload_skills; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add upload_skills.py
git commit -m "refactor: route skill upload and attachment through the ID store"
```

---

### Task 11: Rewrite `create_coordinator.py` (D3)

**Files:**
- Modify: `create_coordinator.py`

- [ ] **Step 1: Rewrite the file**

Replace the entire file with:

```python
"""Create the Incident Commander that orchestrates the war-room.

Its roster is the specialists created by create_specialists.py. It carries the
Anthropic `docx` skill — that is what turns its synthesis into the postmortem
document that is the actual deliverable.

Safe to re-run. If the commander already exists, its roster and prompt are
updated in place (creating a new agent version) rather than duplicated.

Usage:
    python create_coordinator.py
"""

import os

from anthropic import Anthropic

from swarm.roster import commander_spec
from swarm.store import IdStore


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    specialists = store.get("specialists")
    if not specialists:
        raise SystemExit("No specialists found. Run create_specialists.py first.")

    spec = commander_spec(list(specialists.values()))
    client = Anthropic()

    existing_id = store.get("coordinator")
    if existing_id:
        agent = client.beta.agents.retrieve(existing_id)
        client.beta.agents.update(existing_id, version=agent.version, **spec)
        print(f"Incident Commander updated in place: {existing_id}")
    else:
        commander = client.beta.agents.create(**spec)
        store.set("coordinator", commander.id)
        print(f"Incident Commander created: {commander.id}")

    print(f"Roster: {list(specialists.keys())}")
    print(f"Skills: {[s['skill_id'] for s in spec['skills']]}")
    print("\nNext: python run_war_room.py")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the commander carries the docx skill**

Run:
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

- [ ] **Step 3: Commit**

```bash
git add create_coordinator.py
git commit -m "feat: attach the docx skill to the commander so it can emit the postmortem"
```

---

### Task 12: Create `run_war_room.py` (D4, D9, D10)

**Files:**
- Create: `run_war_room.py`
- Delete: `run_deal_desk.py`, `download_deliverable.py`

- [ ] **Step 1: Create the run script**

Create `run_war_room.py`:

```python
"""Run the Incident War-Room against the synthetic INC-4417 outage.

Inlines the incident ticket and supporting documents into the kickoff message,
opens the event stream before sending it, narrates the parallel fan-out, then
downloads whatever the agents wrote to /mnt/session/outputs/.

Usage:
    python run_war_room.py
"""

import os
import time
from pathlib import Path

from anthropic import Anthropic

from swarm.context import build_context
from swarm.events import describe, is_terminal
from swarm.store import IdStore

INCIDENT_PATH = Path("synthetic-data/incident-INC-4417.md")
SUPPORTING = [
    Path("synthetic-data/service-topology.md"),
    Path("synthetic-data/recent-changes.json"),
    Path("synthetic-data/past-incidents.json"),
]
OUTPUT_DIR = Path("outputs")

# Session outputs index ~1-3s after the session goes idle.
FILE_LIST_ATTEMPTS = 4
FILE_LIST_DELAY_SECONDS = 2

KICKOFF = """\
INC-4417 is active. You have the bridge.

1. Read the incident ticket yourself.
2. Task all three specialists in parallel — SRE, Security, Comms.
3. Reconcile their findings. Their evidence may appear to conflict; work out
   whether you are looking at two causes, one cause seen twice, or one cause
   plus a coincidence.
4. Write the postmortem as a Word document using the docx skill, saved to
   /mnt/session/outputs/postmortem-INC-4417.docx.

Each specialist has their own skill attached. Move fast — customers are
affected right now.

{context}
"""


def download_outputs(client: Anthropic, session_id: str) -> int:
    """List and download session outputs, retrying through the indexing lag."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    for attempt in range(1, FILE_LIST_ATTEMPTS + 1):
        files = client.beta.files.list(
            scope_id=session_id,
            betas=["managed-agents-2026-04-01"],
        )
        if files.data:
            for f in files.data:
                out_path = OUTPUT_DIR / f.filename
                print(f"  {f.filename}  ->  {out_path}")
                client.beta.files.download(f.id).write_to_file(str(out_path))
            return len(files.data)

        if attempt < FILE_LIST_ATTEMPTS:
            print(f"  (no files yet — retrying in {FILE_LIST_DELAY_SECONDS}s)")
            time.sleep(FILE_LIST_DELAY_SECONDS)

    return 0


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    commander_id = store.get("coordinator")
    environment_id = store.get("environment")
    if not commander_id or not environment_id:
        raise SystemExit(
            "Missing commander or environment. Run, in order:\n"
            "  python setup_environment.py\n"
            "  python create_specialists.py\n"
            "  python upload_skills.py\n"
            "  python create_coordinator.py"
        )

    client = Anthropic()

    print("Loading incident ticket + supporting docs...")
    context = build_context([INCIDENT_PATH], optional=SUPPORTING)

    print(f"\nOpening the bridge against commander {commander_id}...")
    session = client.beta.sessions.create(
        agent=commander_id,
        environment_id=environment_id,
        title="INC-4417 — Checkout API elevated 5xx",
    )
    store.set("last_session", session.id)

    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID", "default")
    console_url = f"https://platform.claude.com/workspaces/{workspace}/sessions/{session.id}"
    print(f"Watch live: {console_url}")

    # Stream-first: open the stream before sending, or early events arrive
    # buffered in one batch and the fan-out isn't visible in real time.
    print("\n=== INCIDENT BRIDGE (this is the demo) ===\n")
    final_text: list[str] = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[{
                "type": "user.message",
                "content": [{"type": "text", "text": KICKOFF.format(context=context)}],
            }],
        )
        for event in stream:
            line = describe(event)
            if line:
                print(line, flush=True)
            elif getattr(event, "type", None) == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        final_text.append(block.text)
                        print(block.text, end="", flush=True)

            if is_terminal(event):
                print("\n\n[bridge closed]")
                break

    OUTPUT_DIR.mkdir(exist_ok=True)
    transcript = OUTPUT_DIR / "commander-transcript.txt"
    transcript.write_text("".join(final_text))
    print(f"\nCommander transcript saved to {transcript}")

    print("\nRetrieving the postmortem from the session container...")
    count = download_outputs(client, session.id)
    if count:
        print(f"\nDownloaded {count} file(s) to {OUTPUT_DIR}/")
    else:
        print("\n  No files produced. The commander may have replied in chat")
        print("  instead of using the docx skill — check the session trace.")

    print(f"\nFull session (including every specialist thread):\n  {console_url}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Remove the superseded scripts**

`download_deliverable.py` duplicated logic now covered by `download_outputs`.

```bash
rm -f run_deal_desk.py download_deliverable.py
```

- [ ] **Step 3: Verify it imports**

Run: `python -c "import run_war_room; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add -A run_war_room.py run_deal_desk.py download_deliverable.py
git commit -m "feat: add war-room run loop with correct terminal gate and output retry"
```

---

### Task 13: Postmortem reviewer, and clear the stale-ID guard

**Files:**
- Modify: `stretch_critic_subagent.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Rewrite `stretch_critic_subagent.py`**

Replace the entire file with:

```python
"""Stretch: add a Postmortem Reviewer to the commander's roster.

The reviewer gates the postmortem before publication, returning one of three
verdicts: PUBLISH, REVISE, or ESCALATE.

Safe to re-run — the reviewer ID is recorded in .swarm_ids.json.

Usage:
    python stretch_critic_subagent.py
"""

import os

from anthropic import Anthropic

from swarm.roster import reviewer_spec
from swarm.store import IdStore

REVIEWER_GUIDANCE = """

# Postmortem review

Before saving the final .docx, send your draft postmortem to the Postmortem
Reviewer. They reply with one of: PUBLISH, REVISE, or ESCALATE.
- If PUBLISH: write the final .docx.
- If REVISE: address every issue and re-submit. Repeat at most twice.
- If ESCALATE: do NOT write the .docx. Report the reviewer's reasoning to the
  user and state what the incident still needs.
"""


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    commander_id = store.get("coordinator")
    if not commander_id:
        raise SystemExit("No commander found. Run create_coordinator.py first.")

    client = Anthropic()

    def create() -> str:
        return client.beta.agents.create(**reviewer_spec()).id

    reviewer_id, created = store.get_or_create("reviewer", create)
    print(f"{'Created' if created else 'Reusing'} reviewer: {reviewer_id}")

    commander = client.beta.agents.retrieve(commander_id)
    roster = list(commander.multiagent.agents)

    def entry_id(entry) -> str:
        return entry if isinstance(entry, str) else getattr(entry, "id", None)

    if reviewer_id in [entry_id(e) for e in roster]:
        print("Reviewer already on the roster — nothing to do.")
        return

    system = commander.system
    if "# Postmortem review" not in system:
        system = system + REVIEWER_GUIDANCE

    client.beta.agents.update(
        commander_id,
        version=commander.version,
        system=system,
        multiagent={"type": "coordinator", "agents": roster + [reviewer_id]},
    )

    print("Commander roster updated. Now includes the postmortem reviewer.")
    print("Re-run run_war_room.py to see the reviewer in action.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Remove the xfail marker now every script is clean**

In `tests/test_models.py`, delete this line above `test_no_stale_model_ids_anywhere_in_repo`:

```python
@pytest.mark.xfail(reason="cleared by Tasks 9-13; remove this marker in Task 13", strict=True)
```

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: PASS, 0 xfailed. If the repo-wide guard fails, its message names the offending file and model ID.

- [ ] **Step 4: Commit**

```bash
git add stretch_critic_subagent.py tests/test_models.py
git commit -m "feat: add postmortem reviewer and enforce the no-stale-model guard"
```

---

### Task 14: Rewrite the docs (D5, D6)

**Files:**
- Modify: `README.md`
- Modify: `scenario-cards.md`
- Modify: `stretch-goals.md`

- [ ] **Step 1: Replace `README.md` entirely**

```markdown
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

```bash
cd 03-specialist-swarm
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
   - Inlines the INC-4417 ticket and supporting documents
   - Opens the event stream, *then* sends the kickoff
   - Narrates the bridge so you can watch the parallel fan-out
   - Saves everything the agents produced to `outputs/`

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
03-specialist-swarm/
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
```

- [ ] **Step 2: Replace `scenario-cards.md`**

```markdown
# Scenario Cards — Option 3

Each team picks ONE. Each is shaped like real incident response: a commander who
runs the bridge and specialists who own lanes.

---

## Card A — Checkout outage (default, fully wired in starter code)

**Coordinator:** "Incident Commander"
- Reads the incident ticket
- Tasks specialists in parallel
- Reconciles conflicting findings into a blameless postmortem

**Specialists:**
1. **SRE Responder** (skill: severity-runbook) — severity, root cause, rollback call
2. **Security Analyst** (skill: threat-triage) — attack or failure, blast radius, disclosure
3. **Comms Lead** (skill: status-page-voice) — customer-facing status update

**The trigger:** `synthetic-data/incident-INC-4417.md` — checkout API 5xx in
EU and APAC, with a config deploy *and* an anomalous traffic spike in the same
window.

**The deliverable:** `outputs/postmortem-INC-4417.docx`

**Why it's the default:** the dual-cause ambiguity means the commander has to
actually reconcile, not relay. That's the part that shows the architecture
earning its keep.

---

## Card B — Data breach response

**Coordinator:** "Breach Response Lead"

**Specialists:**
1. **Forensics** — what was accessed, when, by whom
2. **Legal & Privacy** — which disclosure clocks have started, in which jurisdictions
3. **Customer Trust** — notification drafting, support-team briefing
4. **Engineering** — containment and remediation

**The deliverable:** a regulator-ready incident report plus a customer
notification draft.

---

## Card C — Degraded-dependency triage

**Coordinator:** "Platform On-Call Lead"

**Specialists:**
1. **Dependency Analyst** — which upstream is failing and how far it propagates
2. **Capacity** — can we absorb it, or do we shed load
3. **Product Impact** — which user journeys break, ranked by revenue
4. **Vendor Liaison** — what the provider has said, what to escalate

**The deliverable:** a go/no-go decision memo on failing over.
```

- [ ] **Step 3: Replace `stretch-goals.md`**

```markdown
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
```

- [ ] **Step 4: Verify the documented order matches the scripts**

Run:
```bash
grep -h "Next: python" setup_environment.py create_specialists.py upload_skills.py create_coordinator.py
```
Expected, in order:
```
    print("\nNext: python create_specialists.py")
    print("Next: python upload_skills.py")
    print("\nNext: python create_coordinator.py")
    print("\nNext: python run_war_room.py")
```
This chain must match README steps 1→5.

- [ ] **Step 5: Commit**

```bash
git add README.md scenario-cards.md stretch-goals.md
git commit -m "docs: rewrite for incident war-room with corrected build order"
```

---

### Task 15: Live end-to-end verification

The only task needing a live API key with multi-agent preview access.

**Files:** none modified.

- [ ] **Step 1: Confirm the offline suite is green**

Run: `pytest -v`
Expected: PASS, no failures, no xfails.

- [ ] **Step 2: Confirm no stale model IDs or Deal Desk remnants remain**

Run:
```bash
grep -rnE "opus-4-7|opus-4-6|sonnet-4-6|sonnet-4-5|haiku-4-5-[0-9]{8}" --include="*.py" --include="*.md" . | grep -v "^./PRD.md" | grep -v "^./docs/"
grep -rniE "deal desk|rfp|pricing-playbook" --include="*.py" --include="*.md" . | grep -v "^./PRD.md" | grep -v "^./docs/"
```
Expected: no output from either. (PRD.md and this plan reference the old IDs and Deal Desk deliberately, as defect evidence and migration history.)

- [ ] **Step 3: Cold run**

```bash
rm -f .swarm_ids.json
python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
python run_war_room.py
```

Expected during the run: three `[on the bridge]` lines in quick succession, three `[investigating]` lines interleaved rather than strictly sequential, three `[reported <-]` lines coming back, then `[bridge closed]`.

- [ ] **Step 4: Verify the deliverable exists**

Run: `ls -la outputs/ && file outputs/*.docx`
Expected: a `.docx` listed as `Microsoft Word 2007+`.

If no `.docx` was produced, the run prints the "No files produced" message — open the Console session link and check whether the commander invoked the docx skill. The likely fix is strengthening step 4 of `COMMANDER_SYSTEM` in `swarm/roster.py`, not a code change.

- [ ] **Step 5: Verify postmortem quality**

Open the `.docx` and check each of these. These are the criteria that distinguish synthesis from relay:

- [ ] All seven sections from `POSTMORTEM_SECTIONS` are present
- [ ] **The root cause addresses both the config deploy AND the traffic anomaly** — a postmortem naming only one has relayed rather than reconciled
- [ ] The "Was this an attack?" section carries an explicit verdict, and INCONCLUSIVE is accepted as a valid one
- [ ] Contributing factors name no individual — roles only
- [ ] Action items are specific enough to be verifiably done
- [ ] If prior incidents were referenced, INC-3908 and INC-4102 are the relevant ones

Note which criteria failed. Prompt-level fixes belong in `COMMANDER_SYSTEM`; evidence-level gaps belong in the skills.

- [ ] **Step 6: Verify idempotency (G4)**

```bash
python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
```

Expected: every line reads `Reusing`, `already attached ✓`, or `updated in place`. Nothing reads `Created`.

Then confirm no duplicates server-side:

```bash
python -c "
import collections
from anthropic import Anthropic
names = [a.name for a in Anthropic().beta.agents.list()]
dupes = {n: c for n, c in collections.Counter(names).items() if c > 1}
print(dupes or 'no duplicates')
"
```
Expected: `no duplicates`

- [ ] **Step 7: Commit the verified state**

```bash
git add -A
git commit -m "test: verify end-to-end war-room run produces blameless postmortem"
```

---

## Self-review notes

**Spec coverage.** Every PRD requirement maps to a task: §8.1 trigger docs → Task 8; §8.2 skills → Tasks 6, 7, 10; §8.3 postmortem output → Tasks 6, 11, 15; §8.4 idempotency → Tasks 5, 9, 10, 11, 15; §8.5 run loop → Tasks 3, 12; §8.6 testability → Tasks 1–6. Defects: D1/D2 → Task 2; D3 → Tasks 6, 11; D4 → Tasks 3, 12; D5/D6 → Task 14; D7/D8 → Task 9; D9/D10 → Task 12; D11 → Task 6 (`test_every_specialist_has_a_skill` enforces G7); D12 → Tasks 1–6.

**Scenario-agnostic core.** `models.py`, `store.py`, `events.py` and `context.py` carry no war-room vocabulary except `describe()`'s narration strings, which are cosmetic and tested as such. Swapping to Card B or C means rewriting `roster.py`, `skills/`, and `synthetic-data/` only.

**Naming consistency.** `IdStore.get_or_create` returns `(value, created)` at every call site. `commander_spec(roster)` takes a list of agent-ID strings — the shape the Managed Agents roster accepts as string shorthand. `describe()` returns `str | None` and every caller checks for `None`. The store key stays `coordinator` (not `commander`) so `swarm/store.py` needs no scenario-specific vocabulary.

**Deliberate omission.** No Haiku specialist ships in the default roster. PRD §11 and stretch goal 2 both record where one would legitimately fit, so its absence reads as a decision rather than an oversight.
