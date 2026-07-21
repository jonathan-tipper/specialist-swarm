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
