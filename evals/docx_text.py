"""Extract plain text from a .docx for eval checks.

A Word document is a zip of XML parts; `word/document.xml` holds the body.
Splitting "read the zip" (thin I/O) from "strip markup" (pure, tested)
mirrors the split `swarm/context.py` uses for reading incident documents.
"""

import re
import zipfile
from pathlib import Path

_TAG = re.compile(r"<[^>]+>")


def strip_markup(xml: str) -> str:
    """Turn WordprocessingML body markup into plain text with paragraph breaks.

    Word has no paragraph-boundary whitespace in the raw XML — <w:p> elements
    just abut each other. Without inserting a break at </w:p>, section
    headings and adjacent runs collapse into one line and every text-based
    check downstream (section matching, keyword search) gets unreliable.
    """
    xml = xml.replace("</w:p>", "\n")
    return _TAG.sub("", xml)


def read_docx_text(path: Path) -> str:
    """Read a .docx file from disk and return its plain-text body."""
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return strip_markup(xml)
