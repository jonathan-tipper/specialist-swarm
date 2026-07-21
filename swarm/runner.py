"""Drive an Incident War-Room session end to end.

The one place that knows how to open a session against the Commander, stream
its events, and download whatever it wrote to /mnt/session/outputs/. Both
run_war_room.py (CLI) and webapp.py (browser) consume the same run_session
generator, so there is exactly one event loop.
"""

import time
from pathlib import Path
from typing import Iterator, Optional

from anthropic import Anthropic

from swarm.events import is_terminal, shape

# Session outputs index ~1-3s after the session goes idle.
FILE_LIST_ATTEMPTS = 4
FILE_LIST_DELAY_SECONDS = 2


def resolve_console_url(session_id: str, workspace: Optional[str]) -> str:
    """Build the Console link. Falls back to the workspace-less form when
    ANTHROPIC_WORKSPACE_ID is unset rather than embedding the literal string
    "default", which is not a real workspace ID and resolves to a dead link.
    """
    if workspace:
        return f"https://platform.claude.com/workspaces/{workspace}/sessions/{session_id}"
    return f"https://platform.claude.com/sessions/{session_id}"


def download_outputs(client: Anthropic, session_id: str, output_dir: Path) -> list[str]:
    """List and download session outputs, retrying through the indexing lag.

    Returns the filenames written to output_dir.
    """
    output_dir.mkdir(exist_ok=True)

    for attempt in range(1, FILE_LIST_ATTEMPTS + 1):
        files = client.beta.files.list(
            scope_id=session_id,
            betas=["managed-agents-2026-04-01"],
        )
        if files.data:
            filenames = []
            for f in files.data:
                out_path = output_dir / f.filename
                client.beta.files.download(f.id).write_to_file(str(out_path))
                filenames.append(f.filename)
            return filenames

        if attempt < FILE_LIST_ATTEMPTS:
            time.sleep(FILE_LIST_DELAY_SECONDS)

    return []


def run_session(
    client: Anthropic,
    commander_id: str,
    environment_id: str,
    kickoff_text: str,
    title: str,
    workspace: Optional[str] = None,
    output_dir: Path = Path("outputs"),
) -> Iterator[dict]:
    """Open a session against the Commander and yield events as it runs.

    Yields dicts with a "kind" key:
      session_started {session_id, console_url}
      thread           {event: created|running, agent}   -- from swarm.events.shape
      dispatch         {direction: tasked|reported, agent}
      tool             {name}
      commander_text   {text}     -- streamed commander reply chunks
      terminated       {}
      outputs          {files: [str]}
      error            {message}  -- any exception; the generator ends after this
    """
    try:
        session = client.beta.sessions.create(
            agent=commander_id,
            environment_id=environment_id,
            title=title,
        )
        yield {
            "kind": "session_started",
            "session_id": session.id,
            "console_url": resolve_console_url(session.id, workspace),
        }

        # Stream-first: open the stream before sending, or early events
        # arrive buffered in one batch and the fan-out isn't visible live.
        with client.beta.sessions.events.stream(session.id) as stream:
            client.beta.sessions.events.send(
                session.id,
                events=[{
                    "type": "user.message",
                    "content": [{"type": "text", "text": kickoff_text}],
                }],
            )
            for event in stream:
                shaped = shape(event)
                if shaped:
                    yield shaped
                elif getattr(event, "type", None) == "agent.message":
                    for block in event.content:
                        if getattr(block, "type", None) == "text":
                            yield {"kind": "commander_text", "text": block.text}

                if is_terminal(event):
                    yield {"kind": "terminated"}
                    break

        files = download_outputs(client, session.id, output_dir)
        yield {"kind": "outputs", "files": files}

    except Exception as exc:  # surfaced to the caller instead of crashing it
        yield {"kind": "error", "message": str(exc)}
