import re
from pathlib import Path

import pytest

from swarm import models

STALE = ("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6", "claude-sonnet-4-5")


def test_commander_is_opus_4_8():
    assert models.COMMANDER == "claude-opus-4-8"


def test_reviewer_is_opus_4_8():
    assert models.REVIEWER == "claude-opus-4-8"


def test_specialist_is_sonnet_5():
    assert models.SPECIALIST == "claude-sonnet-5"


def test_lightweight_tier_is_available_for_future_roles():
    """Unused today (see PRD §11) but defined so a Haiku role has one source."""
    assert models.LIGHTWEIGHT == "claude-haiku-4-5"


def test_no_date_suffixed_ids():
    """Bare aliases only — a trailing -YYYYMMDD is the documented foot-gun."""
    for value in (models.COMMANDER, models.REVIEWER, models.SPECIALIST, models.LIGHTWEIGHT):
        assert not re.search(r"-\d{8}$", value), value


@pytest.mark.xfail(reason="cleared by Tasks 9-13; remove this marker in Task 13", strict=True)
def test_no_stale_model_ids_anywhere_in_repo():
    root = Path(__file__).resolve().parent.parent
    offenders = []
    for path in root.rglob("*.py"):
        if ".git" in path.parts or "tests" in path.parts:
            continue
        text = path.read_text()
        for stale in STALE:
            if stale in text:
                offenders.append(f"{path.relative_to(root)}: {stale}")
    assert not offenders, offenders
