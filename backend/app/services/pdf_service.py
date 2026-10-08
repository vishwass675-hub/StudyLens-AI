"""
PDF text extraction and cleaning service using PyMuPDF.
"""

from typing import List, Union, BinaryIO
import re
import pymupdf as fitz
from backend.app.models.document import ExtractedPage
from backend.app.core.config import settings


class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass


class InvalidPDFError(PDFProcessingError):
    """Raised when the uploaded file is not a valid or readable PDF."""
    pass


class EmptyPDFError(PDFProcessingError):
    """Raised when the PDF has no pages or contains zero extractable text."""
    pass


class PDFService:
    """Handles PDF validation, safe opening, text extraction, and text cleaning."""

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Cleans obvious extraction noise while strictly preserving actual meaning and wording:
        - Removes non-printable control characters (except \\n, \\t, \\r)
        - Replaces excessive horizontal spaces and tabs with a single space
        - Fixes broken hyphenated linebreaks (e.g., 'transfor-\\nmation' -> 'transformation')
        - Standardizes consecutive blank lines (max 2 linebreaks)
        """
        if not text:
            return ""

        # Remove null bytes or non-printable control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # De-hyphenate words broken across linebreaks (standard academic paper layout)
        text = re.sub(r"(\b\w+)-\n(\w+\b)", r"\1\2", text)

        # Normalize horizontal whitespace (tabs, multiple spaces)
        text = re.sub(r"[ \t]+", " ", text)

        # Collapse excessive consecutive newlines to maximum 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def extract_pages(
        self,
        document_id: str,
        file_input: Union[str, bytes, BinaryIO],
        filename: str = "document.pdf",
    ) -> List[ExtractedPage]:
        """
        Extracts and cleans text page-by-page from a PDF using PyMuPDF.

        Args:
            document_id: Unique identifier for the document
            file_input: File path or raw bytes/stream
            filename: Name of the uploaded file

        Returns:
            List of ExtractedPage objects with 1-indexed page numbers
        """
        try:
            if isinstance(file_input, str):
                doc = fitz.open(file_input)
            elif isinstance(file_input, bytes):
                # Verify PDF magic bytes
                if not file_input.startswith(b"%PDF"):
                    raise InvalidPDFError(f"'{filename}' does not have a valid PDF header.")
                doc = fitz.open(stream=file_input, filetype="pdf")
            elif hasattr(file_input, "read"):
                content = file_input.read()
                if hasattr(file_input, "seek"):
                    file_input.seek(0)
                if not content.startswith(b"%PDF"):
                    raise InvalidPDFError(f"'{filename}' does not have a valid PDF header.")
                doc = fitz.open(stream=content, filetype="pdf")
            else:
                raise InvalidPDFError("Unsupported input format for PDF.")
        except InvalidPDFError:
            raise
        except Exception as e:
            raise InvalidPDFError(f"Failed to open PDF document '{filename}': {str(e)}")

        extracted_pages: List[ExtractedPage] = []
        total_chars = 0

        try:
            total_page_count = len(doc)
            if total_page_count == 0:
                raise EmptyPDFError(f"PDF '{filename}' contains 0 pages.")
            if total_page_count > settings.MAX_PAGES_LIMIT:
                raise InvalidPDFError(
                    f"PDF '{filename}' has {total_page_count} pages, which exceeds the limit of {settings.MAX_PAGES_LIMIT} pages."
                )

            for page_idx in range(total_page_count):
                page = doc[page_idx]
                raw_text = page.get_text("text") or ""
                cleaned = self.clean_text(raw_text)

                words = len(cleaned.split())
                chars = len(cleaned)
                total_chars += chars

                extracted_pages.append(
                    ExtractedPage(
                        document_id=document_id,
                        page=page_idx + 1,  # 1-indexed
                        text=cleaned,
                        char_count=chars,
                        word_count=words,
                    )
                )

        finally:
            doc.close()

        if total_chars == 0:
            raise EmptyPDFError(
                f"No extractable text found in '{filename}'. "
                "The PDF might be image-only (scanned), empty, or password protected."
            )

        return extracted_pages
