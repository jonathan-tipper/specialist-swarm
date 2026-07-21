"""Upload each custom skill in skills/ and attach it to its specialist.

Idempotent in both directions: existing skills are matched by display title
and reused, and a skill already attached to an agent is not re-attached.

Usage:
    python upload_skills.py
"""

import os
from pathlib import Path

from anthropic import Anthropic
from anthropic.lib import files_from_dir

from swarm.roster import SKILL_TO_SPECIALIST
from swarm.store import IdStore


def already_attached(current_skills, skill_id: str) -> bool:
    """True if skill_id is already on this agent. SDK returns models, not dicts."""
    return any(getattr(s, "skill_id", None) == skill_id for s in current_skills)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    if store.get("specialists") is None:
        raise SystemExit("No specialists found. Run create_specialists.py first.")

    client = Anthropic()

    # The Skills API enforces unique display titles, so a retry with the same
    # title would 409. List first and reuse.
    print("Checking for existing skills...")
    existing_by_title = {
        s.display_title: s.id for s in client.beta.skills.list(source="custom")
    }

    for skill_name, specialist_key in SKILL_TO_SPECIALIST.items():
        skill_dir = Path("skills") / skill_name
        if not (skill_dir / "SKILL.md").exists():
            print(f"  Skipping {skill_name} — no SKILL.md found")
            continue

        display_title = skill_name.replace("-", " ").title()

        def create(skill_dir=skill_dir, display_title=display_title) -> str:
            if display_title in existing_by_title:
                return existing_by_title[display_title]
            skill = client.beta.skills.create(
                display_title=display_title,
                files=files_from_dir(str(skill_dir)),
            )
            return skill.id

        skill_id, created = store.get_or_create(f"skills.{skill_name}", create)
        print(f"{'Uploaded' if created else 'Reusing '} skill: {skill_name} ({skill_id})")

        specialist_id = store.get(f"specialists.{specialist_key}")
        if specialist_id is None:
            print(f"  ! No agent for `{specialist_key}` — skipping attach")
            continue

        agent = client.beta.agents.retrieve(specialist_id)
        current = list(agent.skills or [])
        if already_attached(current, skill_id):
            print(f"  already attached to `{specialist_key}` ✓")
            continue

        client.beta.agents.update(
            specialist_id,
            version=agent.version,
            skills=current + [{"type": "custom", "skill_id": skill_id, "version": "latest"}],
        )
        print(f"  attached to `{specialist_key}` ✓")

    print("\nNext: python create_coordinator.py")


if __name__ == "__main__":
    main()
