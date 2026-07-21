"""Run the Incident War-Room against the synthetic INC-4417 outage.

Inlines the incident ticket and supporting documents into the kickoff message,
then drives swarm.runner.run_session and prints its events as they arrive.

Usage:
    python run_war_room.py
"""

import os
from pathlib import Path

from anthropic import Anthropic

from swarm.context import build_context
from swarm.events import format_line
from swarm.runner import run_session
from swarm.store import IdStore

INCIDENT_PATH = Path("synthetic-data/incident-INC-4417.md")
SUPPORTING = [
    Path("synthetic-data/service-topology.md"),
    Path("synthetic-data/recent-changes.json"),
    Path("synthetic-data/past-incidents.json"),
]
OUTPUT_DIR = Path("outputs")
TITLE = "INC-4417 — Checkout API elevated 5xx"

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


def kickoff_message() -> str:
    """Load the incident ticket + supporting docs and render the kickoff text."""
    context = build_context([INCIDENT_PATH], optional=SUPPORTING)
    return KICKOFF.format(context=context)


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
    text = kickoff_message()

    final_text: list[str] = []
    console_url = None

    for event in run_session(
        client,
        commander_id,
        environment_id,
        text,
        TITLE,
        workspace=os.environ.get("ANTHROPIC_WORKSPACE_ID"),
        output_dir=OUTPUT_DIR,
    ):
        kind = event["kind"]
        if kind == "session_started":
            console_url = event["console_url"]
            print(f"\nOpening the bridge against commander {commander_id}...")
            print(f"Watch live: {console_url}")
            print("\n=== INCIDENT BRIDGE (this is the demo) ===\n")
        elif kind in ("thread", "dispatch", "tool"):
            print(format_line(event), flush=True)
        elif kind == "commander_text":
            final_text.append(event["text"])
            print(event["text"], end="", flush=True)
        elif kind == "terminated":
            print("\n\n[bridge closed]")
        elif kind == "outputs":
            files = event["files"]
            if files:
                print(f"\nDownloaded {len(files)} file(s) to {OUTPUT_DIR}/")
                for f in files:
                    print(f"  {f}")
            else:
                print("\n  No files produced. The commander may have replied in chat")
                print("  instead of using the docx skill — check the session trace.")
        elif kind == "error":
            print(f"\n[error] {event['message']}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    transcript = OUTPUT_DIR / "commander-transcript.txt"
    transcript.write_text("".join(final_text))
    print(f"\nCommander transcript saved to {transcript}")

    if console_url:
        print(f"\nFull session (including every specialist thread):\n  {console_url}")


if __name__ == "__main__":
    main()
