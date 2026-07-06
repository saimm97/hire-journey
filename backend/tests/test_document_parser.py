"""Tests for document text extraction (PDF via PyMuPDF, DOCX via python-docx)."""

import io

import fitz
import pytest
from docx import Document

from app.exceptions import DocumentParseError
from app.utils import document_parser


def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _docx_bytes(lines: list[str]) -> bytes:
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_pdf_text_is_extracted():
    text = document_parser.to_text(_pdf_bytes("Jane Smith - Backend Engineer"), "cv.pdf")
    assert "Jane Smith" in text


def test_docx_text_is_extracted():
    text = document_parser.to_text(_docx_bytes(["Jane Smith", "Backend Engineer"]), "cv.docx")
    assert "Backend Engineer" in text


def test_extension_match_is_case_insensitive():
    text = document_parser.to_text(_pdf_bytes("Resume"), "CV.PDF")
    assert "Resume" in text


def test_unsupported_extension_is_rejected():
    with pytest.raises(DocumentParseError):
        document_parser.to_text(b"plain text", "resume.txt")


def test_empty_document_is_rejected():
    with pytest.raises(DocumentParseError):
        document_parser.to_text(_pdf_bytes("   "), "blank.pdf")
