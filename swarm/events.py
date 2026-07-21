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


def shape(event) -> dict | None:
    """Reduce a bridge-worthy SDK event to a small structured dict.

    The web UI renders these semantically (agent cards, connectors); the CLI
    formats them into narration lines via `format_line`. Returns None for
    events that aren't part of the bridge story.
    """
    event_type = getattr(event, "type", None)

    if event_type == "session.thread_created":
        return {"kind": "thread", "event": "created",
                "agent": getattr(event, "agent_name", "?")}
    if event_type == "session.thread_status_running":
        return {"kind": "thread", "event": "running",
                "agent": getattr(event, "agent_name", "?")}
    if event_type == "agent.thread_message_sent":
        return {"kind": "dispatch", "direction": "tasked",
                "agent": getattr(event, "to_agent_name", "?")}
    if event_type == "agent.thread_message_received":
        return {"kind": "dispatch", "direction": "reported",
                "agent": getattr(event, "from_agent_name", "?")}
    if event_type == "agent.tool_use":
        return {"kind": "tool", "name": getattr(event, "name", "?")}

    return None


def format_line(shaped: dict) -> str:
    """Render a shaped bridge event as one CLI narration line."""
    if shaped["kind"] == "thread":
        label = "on the bridge" if shaped["event"] == "created" else "investigating"
        return f"  [{label}]    {shaped['agent']}"
    if shaped["kind"] == "dispatch":
        arrow = "tasked ->" if shaped["direction"] == "tasked" else "reported <-"
        pad = " " * (11 - len(arrow))
        return f"  [{arrow}]{pad}      {shaped['agent']}"
    if shaped["kind"] == "tool":
        return f"  [tool: {shaped['name']}]"
    raise ValueError(f"Unknown shaped event kind: {shaped['kind']!r}")


def describe(event) -> str | None:
    """A one-line render of the events worth narrating during a live demo.

    Returns None for events that shouldn't be printed.
    """
    shaped = shape(event)
    return format_line(shaped) if shaped else None
