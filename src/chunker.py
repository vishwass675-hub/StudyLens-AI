"""
Text chunking module for academic documents with sentence-boundary preservation and page tracking.
"""

from dataclasses import dataclass
from typing import List
from src.pdf_processor import ProcessedPDF, PDFPage


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    page_number: int
    chunk_index: int
    char_count: int
    word_count: int
    metadata: dict


class TextChunker:
    """
    Splits academic text into semantically cohesive chunks while preserving
    page numbers and sentence boundaries with configurable sliding overlap.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """
        Args:
            chunk_size: Target character count per chunk.
            chunk_overlap: Overlap characters between consecutive chunks.
            min_chunk_size: Minimum characters to avoid micro-chunks.
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def _split_text_by_separators(self, text: str, max_size: int) -> List[str]:
        """
        Recursively splits text using natural academic boundaries:
        1. Paragraphs (\n\n)
        2. Linebreaks (\n)
        3. Sentences (. )
        4. Words (' ')
        """
        if len(text) <= max_size:
            return [text] if text.strip() else []

        separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
        return self._recursive_split(text, max_size, separators)

    def _recursive_split(self, text: str, max_size: int, separators: List[str]) -> List[str]:
        if not separators or len(text) <= max_size:
            return [text.strip()] if text.strip() else []

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep == "":
            # Hard character cut if no punctuation or space found
            return [text[i : i + max_size].strip() for i in range(0, len(text), max_size) if text[i : i + max_size].strip()]

        splits = text.split(sep)
        result = []
        current_segment = ""

        for part in splits:
            candidate = f"{current_segment}{sep}{part}" if current_segment else part
            if len(candidate) <= max_size:
                current_segment = candidate
            else:
                if current_segment:
                    result.append(current_segment.strip())
                if len(part) > max_size:
                    # Recursively split the oversized part using smaller separators
                    sub_splits = self._recursive_split(part, max_size, remaining_seps)
                    result.extend(sub_splits)
                    current_segment = ""
                else:
                    current_segment = part

        if current_segment and current_segment.strip():
            result.append(current_segment.strip())

        return result

    def chunk_pdf(self, processed_pdf: ProcessedPDF) -> List[TextChunk]:
        """
        Splits a processed PDF into indexed chunks with accurate page provenance.

        Each page is chunked individually, or with smooth sliding window overlap,
        ensuring every chunk is tagged with its source page.
        """
        chunks: List[TextChunk] = []
        chunk_counter = 0

        for page in processed_pdf.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            # If page text fits cleanly into one chunk
            if len(page_text) <= self.chunk_size:
                chunk_id = f"chunk_{chunk_counter:04d}_p{page.page_number}"
                chunks.append(
                    TextChunk(
                        chunk_id=chunk_id,
                        text=page_text,
                        page_number=page.page_number,
                        chunk_index=chunk_counter,
                        char_count=len(page_text),
                        word_count=len(page_text.split()),
                        metadata={
                            "filename": processed_pdf.filename,
                            "page": page.page_number,
                        },
                    )
                )
                chunk_counter += 1
                continue

            # Split the page into coherent blocks
            blocks = self._split_text_by_separators(page_text, self.chunk_size)

            # Build overlapping chunks from blocks
            i = 0
            while i < len(blocks):
                current_chunk_text = blocks[i]
                j = i + 1

                # Accumulate blocks up to chunk_size
                while j < len(blocks):
                    next_candidate = f"{current_chunk_text}\n\n{blocks[j]}"
                    if len(next_candidate) <= self.chunk_size:
                        current_chunk_text = next_candidate
                        j += 1
                    else:
                        break

                if len(current_chunk_text.strip()) >= self.min_chunk_size or not chunks:
                    chunk_id = f"chunk_{chunk_counter:04d}_p{page.page_number}"
                    chunks.append(
                        TextChunk(
                            chunk_id=chunk_id,
                            text=current_chunk_text.strip(),
                            page_number=page.page_number,
                            chunk_index=chunk_counter,
                            char_count=len(current_chunk_text.strip()),
                            word_count=len(current_chunk_text.strip().split()),
                            metadata={
                                "filename": processed_pdf.filename,
                                "page": page.page_number,
                            },
                        )
                    )
                    chunk_counter += 1

                # Move index forward with respect to overlap
                if j == i:
                    i += 1
                elif j == len(blocks):
                    break
                else:
                    # In academic text, step forward by 1 block for healthy overlap
                    i = max(i + 1, j - 1)

        return chunks
