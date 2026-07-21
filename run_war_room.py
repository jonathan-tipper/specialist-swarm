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


def resolve_console_url(session_id: str, workspace: str | None) -> str:
    """Build the Console link. Falls back to the workspace-less form when
    ANTHROPIC_WORKSPACE_ID is unset rather than embedding the literal string
    "default", which is not a real workspace ID and resolves to a dead link.
    """
    if workspace:
        return f"https://platform.claude.com/workspaces/{workspace}/sessions/{session_id}"
    return f"https://platform.claude.com/sessions/{session_id}"


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

    console_url = resolve_console_url(session.id, os.environ.get("ANTHROPIC_WORKSPACE_ID"))
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
