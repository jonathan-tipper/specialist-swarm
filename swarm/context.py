"""Assemble the synthetic incident documents into one prompt block.

At workshop scale, inlining the ticket and supporting files into the kickoff
message is simpler than the Files API and keeps the run inspectable in one
place. The incident ticket is required; the supporting files are optional so
a team can delete one and still get a run.
"""

from pathlib import Path
from typing import Iterable, Sequence


class MissingDocumentError(FileNotFoundError):
    """A required source document was not found on disk."""


def _render(path: Path) -> str:
    return f"=====  DOCUMENT: {path.name}  =====\n{path.read_text()}"


def build_context(
    required: Sequence[Path],
    optional: Iterable[Path] = (),
) -> str:
    """Render documents into a single delimited prompt block."""
    if not required:
        raise ValueError("build_context needs at least one required document")

    blocks = []
    for path in required:
        if not path.exists():
            raise MissingDocumentError(f"Required document not found: {path}")
        blocks.append(_render(path))

    for path in optional:
        if path.exists():
            blocks.append(_render(path))

    return "\n\n".join(blocks)
