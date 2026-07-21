"""Aggregate structural + judged results into one printable scorecard."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Scorecard:
    missing_sections: list[str] = field(default_factory=list)
    parallel_fanout: Optional[bool] = None  # None = not checked (no event log supplied)
    judged: dict[str, Any] = field(default_factory=dict)  # criterion key -> {"verdict","evidence"}

    @property
    def structural_passed(self) -> bool:
        if self.missing_sections:
            return False
        if self.parallel_fanout is False:
            return False
        return True

    @property
    def judged_passed(self) -> bool:
        return all(result.get("verdict") == "PASS" for result in self.judged.values())

    @property
    def passed(self) -> bool:
        return self.structural_passed and (not self.judged or self.judged_passed)


def render(card: Scorecard) -> str:
    """Render a scorecard as CLI-friendly text."""
    lines = ["=== War-Room Eval Scorecard ===", "", "-- Structural --"]

    if card.missing_sections:
        lines.append(f"FAIL   sections: missing {card.missing_sections}")
    else:
        lines.append("PASS   sections: all present")

    if card.parallel_fanout is None:
        lines.append("SKIP   fan-out: no event log supplied")
    elif card.parallel_fanout:
        lines.append("PASS   fan-out: parallel")
    else:
        lines.append("FAIL   fan-out: specialists were tasked serially")

    if card.judged:
        lines.append("")
        lines.append("-- Judged --")
        for key, result in card.judged.items():
            lines.append(f"{result['verdict']:<7} {key}: {result['evidence']}")

    lines.append("")
    lines.append(f"OVERALL: {'PASS' if card.passed else 'FAIL'}")
    return "\n".join(lines)
