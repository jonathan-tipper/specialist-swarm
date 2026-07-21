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
    system = reviewer_spec()["system"]
    for verdict in ["PUBLISH", "REVISE", "ESCALATE"]:
        assert verdict in system, verdict
