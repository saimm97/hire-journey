"""PDF text extraction using pdfplumber's layout-preserving mode."""

import io

import pdfplumber


class PdfUnreadableError(Exception):
    """The bytes could not be opened or read as a PDF."""


class PdfNoTextError(Exception):
    """The PDF opened but contained no extractable text."""


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def extract_text(data: bytes) -> str:
    """Return reading-order text from a PDF.

    Plain extraction keeps lines compact (no layout padding), which the
    delimiter-based field and skill parsing relies on.
    """
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise PdfUnreadableError from exc

    text = "\n".join(pages).strip()
    if not text:
        raise PdfNoTextError
    return text
