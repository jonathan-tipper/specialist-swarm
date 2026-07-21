"""Create the cloud Environment the war-room session runs in.

Safe to re-run — the environment ID is recorded in .swarm_ids.json and reused.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python setup_environment.py
"""

import os

from anthropic import Anthropic

from swarm.store import IdStore


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    client = Anthropic()

    def create() -> str:
        environment = client.beta.environments.create(
            name="incident-war-room-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        return environment.id

    environment_id, created = store.get_or_create("environment", create)

    print(f"{'Created' if created else 'Reusing'} environment: {environment_id}")
    print("\nNext: python create_specialists.py")


if __name__ == "__main__":
    main()
