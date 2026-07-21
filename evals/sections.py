"""Structural section-coverage check against PRD §8.3 / §10.

`swarm.roster` is the one place the section list is authored (currently a
stub pending Epic 2, issue #10 — see that module's own docstring). Importing
it here rather than keeping a second copy means this check can't silently
drift from whatever Epic 2 lands.
"""

from swarm.roster import POSTMORTEM_SECTIONS

__all__ = ["POSTMORTEM_SECTIONS", "missing_sections"]


def missing_sections(text: str, sections: list[str] = POSTMORTEM_SECTIONS) -> list[str]:
    """Sections from `sections` that don't appear (case-insensitive) in `text`."""
    lowered = text.lower()
    return [section for section in sections if section.lower() not in lowered]
