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
