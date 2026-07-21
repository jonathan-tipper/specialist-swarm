"""Grade a war-room run's postmortem against the PRD's success criteria (§10).

Usage:
    python run_eval.py outputs/postmortem-INC-4417.docx
    python run_eval.py outputs/postmortem-INC-4417.docx --events outputs/events.jsonl --judge

Structural checks (section coverage, parallel fan-out) run offline against
artifacts already on disk. --judge additionally spends one live API call to
grade synthesis quality, blameless framing, and comms voice — the dimensions
§10 / Task G today check by eye. Requires ANTHROPIC_API_KEY.

--events expects a JSONL file of the run's SSE events; run_war_room.py does
not yet write one — see evals/README.md.
"""

import argparse
import json
import sys
from pathlib import Path

from evals.docx_text import read_docx_text
from evals.fanout import is_parallel_fanout
from evals.scorecard import Scorecard, render
from evals.sections import missing_sections

INCIDENT_TICKET = Path("synthetic-data/incident-INC-4417.md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("docx_path", type=Path, help="Path to the generated postmortem .docx")
    parser.add_argument("--events", type=Path, help="JSONL event log from run_war_room.py")
    parser.add_argument("--judge", action="store_true", help="Also run the live LLM judge")
    args = parser.parse_args()

    text = read_docx_text(args.docx_path)
    card = Scorecard(missing_sections=missing_sections(text))

    if args.events:
        events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
        card.parallel_fanout = is_parallel_fanout(events)

    if args.judge:
        from evals.judge import grade  # deferred: needs ANTHROPIC_API_KEY, not needed for structural-only runs

        card.judged = grade(text, INCIDENT_TICKET.read_text())

    print(render(card))
    return 0 if card.passed else 1


if __name__ == "__main__":
    sys.exit(main())
