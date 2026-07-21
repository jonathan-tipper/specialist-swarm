from evals.sections import POSTMORTEM_SECTIONS, missing_sections


def test_all_sections_present_returns_empty():
    text = "\n".join(POSTMORTEM_SECTIONS)
    assert missing_sections(text) == []


def test_matching_is_case_insensitive():
    text = "\n".join(section.upper() for section in POSTMORTEM_SECTIONS)
    assert missing_sections(text) == []


def test_reports_each_missing_section():
    text = "Incident summary\nTimeline\nRoot cause"
    result = missing_sections(text)
    assert result == [
        "Was this an attack?",
        "Customer communications issued",
        "Contributing factors",
        "Action items",
    ]


def test_empty_text_is_missing_everything():
    assert missing_sections("") == POSTMORTEM_SECTIONS
