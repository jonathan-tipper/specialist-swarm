"""Structural section-coverage check against PRD §8.3 / §10.

Kept as a local, independent copy of the section list rather than importing
`swarm.roster.POSTMORTEM_SECTIONS` — evals/ must stay importable and testable
before swarm/ has landed, and the two lists are a PRD-derived contract either
way, so drift between them is what the roster's own tests already guard.
"""

POSTMORTEM_SECTIONS = [
    "Incident summary",
    "Timeline",
    "Root cause",
    "Was this an attack?",
    "Customer communications issued",
    "Contributing factors",
    "Action items",
]


def missing_sections(text: str, sections: list[str] = POSTMORTEM_SECTIONS) -> list[str]:
    """Sections from `sections` that don't appear (case-insensitive) in `text`."""
    lowered = text.lower()
    return [section for section in sections if section.lower() not in lowered]
