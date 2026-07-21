"""Check G2 — the fan-out was genuinely parallel, not serial.

Consumes a plain list of event dicts, as would be serialized from the
Managed Agents SSE stream to a JSONL log. Event vocabulary matches the
master plan's `swarm/events.py`: `session.thread_created`,
`agent.thread_message_sent`, `agent.thread_message_received`.

`run_war_room.py` does not currently persist events to disk — this module
has nothing to consume yet. See evals/README.md.
"""

from typing import Any


def is_parallel_fanout(events: list[dict[str, Any]], expected_agents: int = 3) -> bool:
    """True iff `expected_agents` threads were created before the first reply came back.

    A serial commander tasks one specialist, waits for its reply, then tasks
    the next — a thread_message_received would show up before the later
    thread_created events. This is exactly what PRD Task G Step 2 checks by
    eye ("three [tasked ->] lines ... before the first [reported <-] line");
    this makes it mechanical.
    """
    created = 0
    for event in events:
        event_type = event.get("type")
        if event_type == "session.thread_created":
            created += 1
        elif event_type == "agent.thread_message_received":
            return created >= expected_agents
    return False
