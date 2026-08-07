"""Extract plain text from uploaded resume documents (PDF via PyMuPDF, DOCX via python-docx)."""

import io

import fitz
from docx import Document

from app import messages
from app.exceptions import DocumentParseError

SUPPORTED_EXTENSIONS = (".pdf", ".docx")


def extension_of(filename: str) -> str:
    _, dot, ext = filename.lower().rpartition(".")
    return f".{ext}" if dot else ""


def is_supported(filename: str) -> bool:
    return extension_of(filename) in SUPPORTED_EXTENSIONS


def to_text(data: bytes, filename: str) -> str:
    extension = extension_of(filename)
    if extension == ".pdf":
        text = _pdf_to_text(data)
    elif extension == ".docx":
        text = _docx_to_text(data)
    else:
        raise DocumentParseError(messages.DOCUMENT_UNSUPPORTED)

    text = text.strip()
    if not text:
        raise DocumentParseError(messages.DOCUMENT_NO_TEXT)
    return text


def _pdf_to_text(data: bytes) -> str:
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            return "\n".join(page.get_text() for page in document)
    except Exception as exc:
        raise DocumentParseError(messages.DOCUMENT_UNREADABLE) from exc


def _docx_to_text(data: bytes) -> str:
    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentParseError(messages.DOCUMENT_UNREADABLE) from exc

    lines = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.extend(cell.text for cell in row.cells)
    return "\n".join(lines)
