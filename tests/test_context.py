import pytest

from swarm.context import MissingDocumentError, build_context


def test_single_document(tmp_path):
    doc = tmp_path / "incident.md"
    doc.write_text("INCIDENT BODY")
    assert build_context([doc]) == "=====  DOCUMENT: incident.md  =====\nINCIDENT BODY"


def test_multiple_documents_are_separated(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.json"
    a.write_text("AAA")
    b.write_text("BBB")
    assert build_context([a, b]) == (
        "=====  DOCUMENT: a.md  =====\nAAA\n\n"
        "=====  DOCUMENT: b.json  =====\nBBB"
    )


def test_missing_required_document_raises(tmp_path):
    with pytest.raises(MissingDocumentError) as exc:
        build_context([tmp_path / "nope.md"])
    assert "nope.md" in str(exc.value)


def test_missing_optional_document_is_skipped(tmp_path):
    present = tmp_path / "present.md"
    present.write_text("HERE")
    assert build_context([present], optional=[tmp_path / "absent.md"]) == (
        "=====  DOCUMENT: present.md  =====\nHERE"
    )


def test_present_optional_document_is_included(tmp_path):
    required = tmp_path / "r.md"
    optional = tmp_path / "o.md"
    required.write_text("R")
    optional.write_text("O")
    result = build_context([required], optional=[optional])
    assert "DOCUMENT: o.md" in result
    assert result.endswith("O")


def test_empty_input_raises(tmp_path):
    with pytest.raises(ValueError):
        build_context([])
