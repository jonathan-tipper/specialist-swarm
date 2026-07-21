import zipfile

from evals.docx_text import read_docx_text, strip_markup


def test_strip_markup_removes_tags():
    xml = "<w:p><w:r><w:t>Hello</w:t></w:r></w:p>"
    assert strip_markup(xml) == "Hello\n"


def test_strip_markup_inserts_paragraph_breaks():
    xml = "<w:p><w:t>First</w:t></w:p><w:p><w:t>Second</w:t></w:p>"
    assert strip_markup(xml) == "First\nSecond\n"


def test_strip_markup_handles_no_tags():
    assert strip_markup("plain text") == "plain text"


def test_read_docx_text_extracts_body(tmp_path):
    path = tmp_path / "sample.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<w:p><w:t>Incident summary</w:t></w:p><w:p><w:t>Root cause</w:t></w:p>",
        )

    text = read_docx_text(path)

    assert "Incident summary" in text
    assert "Root cause" in text
