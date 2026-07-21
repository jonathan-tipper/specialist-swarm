"""Stretch: add a Postmortem Reviewer to the commander's roster.

The reviewer gates the postmortem before publication, returning one of three
verdicts: PUBLISH, REVISE, or ESCALATE.

Safe to re-run — the reviewer ID is recorded in .swarm_ids.json.

Usage:
    python stretch_critic_subagent.py
"""

import os

from anthropic import Anthropic

from swarm.roster import commander_spec, reviewer_spec
from swarm.store import IdStore

REVIEWER_GUIDANCE = """

# Postmortem review

Before saving the final .docx, send your draft postmortem to the Postmortem
Reviewer. They reply with one of: PUBLISH, REVISE, or ESCALATE.
- If PUBLISH: write the final .docx.
- If REVISE: address every issue and re-submit. Repeat at most twice.
- If ESCALATE: do NOT write the .docx. Report the reviewer's reasoning to the
  user and state what the incident still needs.
"""


def entry_id(entry) -> str | None:
    """Roster entries come back from the API as resolved objects, never bare
    strings, regardless of which form was sent to create them."""
    return entry if isinstance(entry, str) else getattr(entry, "id", None)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    store = IdStore()
    commander_id = store.get("coordinator")
    if not commander_id:
        raise SystemExit("No commander found. Run create_coordinator.py first.")

    client = Anthropic()

    def create() -> str:
        return client.beta.agents.create(**reviewer_spec()).id

    reviewer_id, created = store.get_or_create("reviewer", create)
    print(f"{'Created' if created else 'Reusing'} reviewer: {reviewer_id}")

    commander = client.beta.agents.retrieve(commander_id)
    roster = list(commander.multiagent.agents)

    if reviewer_id in [entry_id(e) for e in roster]:
        print("Reviewer already on the roster — nothing to do.")
        return

    system = commander.system
    if "# Postmortem review" not in system:
        system = system + REVIEWER_GUIDANCE

    # commander.multiagent.agents always comes back as a list of resolved
    # BetaManagedAgentsAgentReference objects, never bare strings, no matter
    # which form was sent. Normalise to IDs and let commander_spec decide the
    # wire shape again rather than appending a raw string to a list of models.
    all_ids = [entry_id(e) for e in roster if entry_id(e)] + [reviewer_id]
    client.beta.agents.update(
        commander_id,
        version=commander.version,
        system=system,
        multiagent=commander_spec(all_ids)["multiagent"],
    )

    print("Commander roster updated. Now includes the postmortem reviewer.")
    print("Re-run run_war_room.py to see the reviewer in action.")


if __name__ == "__main__":
    main()
