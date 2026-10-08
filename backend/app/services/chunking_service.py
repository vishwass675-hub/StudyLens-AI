"""
Text chunking service for academic documents with sentence-boundary preservation and page tracking.
"""

from typing import List
from backend.app.models.document import ExtractedPage, DocumentChunk
from backend.app.core.config import settings


class ChunkingService:
    """
    Partitions extracted page text into retrieval chunks with sliding window overlap.
    Preserves document ID and page number provenance for every chunk.
    """

    def __init__(
        self,
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP,
        min_chunk_size: int = settings.MIN_CHUNK_SIZE,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def _split_text_by_separators(self, text: str, max_size: int) -> List[str]:
        """Recursively splits text on natural boundaries: paragraphs, sentences, words."""
        if len(text) <= max_size:
            return [text] if text.strip() else []

        separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
        return self._recursive_split(text, max_size, separators)

    def _recursive_split(self, text: str, max_size: int, separators: List[str]) -> List[str]:
        if not separators or len(text) <= max_size:
            return [text.strip()] if text.strip() else []

        sep = separators[0]
        remaining = separators[1:]

        if sep == "":
            return [text[i : i + max_size].strip() for i in range(0, len(text), max_size) if text[i : i + max_size].strip()]

        parts = text.split(sep)
        result = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part
            if len(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    result.append(current.strip())
                if len(part) > max_size:
                    sub_splits = self._recursive_split(part, max_size, remaining)
                    result.extend(sub_splits)
                    current = ""
                else:
                    current = part

        if current and current.strip():
            result.append(current.strip())

        return result

    def create_chunks(
        self,
        document_id: str,
        pages: List[ExtractedPage],
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> List[DocumentChunk]:
        """
        Creates chunks from extracted pages while tracking exact page provenance.
        """
        size = chunk_size or self.chunk_size
        overlap = chunk_overlap or self.chunk_overlap

        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            # Small page text fits into a single chunk
            if len(text) <= size:
                chunk_id = f"{document_id}_p{page.page}_{global_chunk_idx:04d}"
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        chunk_id=chunk_id,
                        page_number=page.page,
                        chunk_index=global_chunk_idx,
                        chunk_text=text,
                        char_count=len(text),
                        word_count=len(text.split()),
                    )
                )
                global_chunk_idx += 1
                continue

            blocks = self._split_text_by_separators(text, size)

            i = 0
            while i < len(blocks):
                current_chunk = blocks[i]
                j = i + 1

                while j < len(blocks):
                    candidate = f"{current_chunk}\n\n{blocks[j]}"
                    if len(candidate) <= size:
                        current_chunk = candidate
                        j += 1
                    else:
                        break

                cleaned_chunk_text = current_chunk.strip()
                if len(cleaned_chunk_text) >= self.min_chunk_size or not chunks:
                    chunk_id = f"{document_id}_p{page.page}_{global_chunk_idx:04d}"
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            chunk_id=chunk_id,
                            page_number=page.page,
                            chunk_index=global_chunk_idx,
                            chunk_text=cleaned_chunk_text,
                            char_count=len(cleaned_chunk_text),
                            word_count=len(cleaned_chunk_text.split()),
                        )
                    )
                    global_chunk_idx += 1

                if j == i:
                    i += 1
                elif j == len(blocks):
                    break
                else:
                    i = max(i + 1, j - 1)

        return chunks
