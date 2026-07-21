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
