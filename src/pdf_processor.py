"""
PDF Processing module using PyMuPDF (fitz) for text extraction and academic document metadata extraction.
"""

from dataclasses import dataclass
from typing import List, Optional, Union, BinaryIO
import io
import re
import pymupdf as fitz


@dataclass
class PDFPage:
    page_number: int  # 1-indexed
    text: str
    char_count: int
    word_count: int


@dataclass
class ProcessedPDF:
    filename: str
    total_pages: int
    total_words: int
    total_chars: int
    metadata: dict
    pages: List[PDFPage]


class PDFProcessor:
    """Handles PDF loading, text extraction, cleaning, and normalization."""

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Cleans and normalizes extracted PDF text.
        - Fixes hyphenated line breaks (e.g., 'transfor-\\nmation' -> 'transformation')
        - Normalizes unicode spaces and tabs
        - Condenses multiple empty lines
        """
        if not text:
            return ""

        # Remove null bytes or non-printable control chars except \n, \t, \r
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # De-hyphenate words broken at line ends (common in academic two-column papers)
        text = re.sub(r"(\b\w+)-\n(\w+\b)", r"\1\2", text)

        # Replace excessive horizontal whitespace with a single space
        text = re.sub(r"[ \t]+", " ", text)

        # Standardize multiple consecutive linebreaks to maximum 2 linebreaks
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def process_pdf(
        self,
        file_input: Union[str, bytes, BinaryIO],
        filename: Optional[str] = "uploaded_document.pdf",
    ) -> ProcessedPDF:
        """
        Extracts structured text and metadata from a PDF file.

        Args:
            file_input: File path, bytes, or file-like stream (e.g. Streamlit UploadedFile)
            filename: Name of the file for reporting and metadata

        Returns:
            ProcessedPDF object containing per-page text and summary metadata
        """
        try:
            if isinstance(file_input, str):
                doc = fitz.open(file_input)
            elif isinstance(file_input, bytes):
                doc = fitz.open(stream=file_input, filetype="pdf")
            elif hasattr(file_input, "read"):
                # File-like object (e.g. Streamlit UploadedFile)
                content = file_input.read()
                # Reset pointer if possible
                if hasattr(file_input, "seek"):
                    file_input.seek(0)
                doc = fitz.open(stream=content, filetype="pdf")
            else:
                raise ValueError("Unsupported input format for PDF processing.")
        except Exception as e:
            raise ValueError(f"Failed to open PDF document: {str(e)}")

        pages: List[PDFPage] = []
        total_words = 0
        total_chars = 0

        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                raw_text = page.get_text("text") or ""
                cleaned_text = self._clean_text(raw_text)

                words = len(cleaned_text.split())
                chars = len(cleaned_text)

                pages.append(
                    PDFPage(
                        page_number=page_index + 1,
                        text=cleaned_text,
                        char_count=chars,
                        word_count=words,
                    )
                )

                total_words += words
                total_chars += chars

            doc_metadata = doc.metadata or {}
        finally:
            doc.close()

        if total_chars == 0:
            raise ValueError(
                f"No extractable text was found in '{filename}'. "
                "The PDF might be image-only (scanned) or encrypted."
            )

        return ProcessedPDF(
            filename=filename or "document.pdf",
            total_pages=len(pages),
            total_words=total_words,
            total_chars=total_chars,
            metadata=doc_metadata,
            pages=pages,
        )
