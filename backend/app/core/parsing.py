"""File parsing: a file on disk -> list of pages with page numbers.

PDF pages map to real page numbers (PyMuPDF). DOCX/TXT/MD documents are
treated as a single page, so citations for them always point to page 1.
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@dataclass(frozen=True)
class Page:
    text: str
    page_number: int


class ParsingError(ValueError):
    """Raised when a file cannot be parsed into text."""


def parse_file(path: Path) -> list[Page]:
    """Parse a supported file into pages. Raises ParsingError on failure."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext == ".docx":
        return _parse_docx(path)
    if ext in {".txt", ".md"}:
        return _parse_text(path)
    raise ParsingError(f"Unsupported file type: {ext}")


def _parse_pdf(path: Path) -> list[Page]:
    try:
        with pymupdf.open(path) as doc:
            return [
                Page(text=page.get_text("text"), page_number=number)
                for number, page in enumerate(doc, start=1)
            ]
    except pymupdf.FileDataError as exc:
        raise ParsingError("The PDF file appears to be corrupted or unreadable.") from exc


def _parse_docx(path: Path) -> list[Page]:
    try:
        document = Document(str(path))
    except Exception as exc:  # python-docx raises several unrelated types
        raise ParsingError("The DOCX file appears to be corrupted or unreadable.") from exc
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return [Page(text="\n\n".join(paragraphs), page_number=1)]


def _parse_text(path: Path) -> list[Page]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [Page(text=text, page_number=1)]
