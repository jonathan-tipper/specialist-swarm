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
