"""Live LLM-as-judge call.

Not unit tested — mirrors the project's own testing philosophy (PRD §8.6):
pure logic lives in evals/ and is tested offline; this thin wrapper is
exercised only by a live eval run, the same way run_war_room.py is exercised
only by Task G's live smoke test.
"""

import json
from typing import Any, Optional

from anthropic import Anthropic

from evals.rubric import CRITERIA, build_judge_prompt

# Same tier as the Postmortem Reviewer and Incident Commander (PRD §6) — this
# judge is doing the same synthesis-grade reasoning, not mechanical extraction.
JUDGE_MODEL = "claude-opus-4-8"


def grade(
    postmortem_text: str,
    incident_ticket_text: str,
    client: Optional[Anthropic] = None,
) -> dict[str, Any]:
    """Call the judge model and return {criterion_key: {"verdict", "evidence"}}."""
    client = client or Anthropic()
    prompt = build_judge_prompt(postmortem_text, incident_ticket_text)
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    result = json.loads(response.content[0].text)
    missing = [criterion["key"] for criterion in CRITERIA if criterion["key"] not in result]
    if missing:
        raise ValueError(f"Judge response missing criteria: {missing}")
    return result
