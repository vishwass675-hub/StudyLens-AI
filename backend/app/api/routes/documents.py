"""
Document management routes for PDF upload, metadata inspection, pages, chunks, and semantic search.
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.services.document_service import document_service
from backend.app.services.pdf_service import InvalidPDFError, EmptyPDFError
from backend.app.services.retrieval_service import retrieval_service
from backend.app.models.document import DocumentStatus
from backend.app.schemas.document import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    PageResponse,
    ChunkResponse,
    DocumentListResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest an academic PDF",
)
async def upload_document(
    file: UploadFile = File(..., description="Academic PDF file to upload and process"),
    chunk_size: Optional[int] = Form(None, description="Target characters per chunk"),
    chunk_overlap: Optional[int] = Form(None, description="Overlap characters between chunks"),
):
    """
    Ingests an academic PDF:
    1. Validates that the file is a PDF.
    2. Generates a unique document ID.
    3. Safely stores the file.
    4. Extracts text page-by-page preserving page numbers.
    5. Partitions text into retrieval chunks.
    6. Generates dense vector embeddings.
    7. Stores vectors in local vector database.
    8. Returns document metadata and status.
    """
    try:
        doc = await document_service.ingest_document(
            file=file,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return DocumentUploadResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            page_count=doc.page_count,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            last_accessed_at=doc.last_accessed_at,
        )
    except InvalidPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except EmptyPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
)
def list_documents():
    docs = document_service.list_documents()
    detail_list = [
        DocumentDetailResponse(
            document_id=d.document_id,
            filename=d.filename,
            page_count=d.page_count,
            total_words=d.total_words,
            total_chars=d.total_chars,
            total_chunks=len(d.chunks),
            status=d.status,
            error_message=d.error_message,
            created_at=d.created_at,
            updated_at=d.updated_at,
            last_accessed_at=d.last_accessed_at,
        )
        for d in docs
    ]
    return DocumentListResponse(documents=detail_list)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document processing status and metadata",
)
def get_document(document_id: str):
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return DocumentDetailResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        page_count=doc.page_count,
        total_words=doc.total_words,
        total_chars=doc.total_chars,
        total_chunks=len(doc.chunks),
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        last_accessed_at=doc.last_accessed_at,
    )


@router.get(
    "/{document_id}/file",
    summary="Download or view the uploaded PDF file",
)
def get_document_file(document_id: str):
    """Returns the persistent uploaded PDF file for viewing or downloading."""
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    file_path = settings.UPLOAD_DIR / f"{document_id}.pdf"
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Original PDF file for '{document_id}' not found on disk.",
        )
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=doc.filename,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all associated vectors, conversations, and cached study tools",
)
def delete_document(document_id: str):
    """
    Safely deletes:
    1. Document metadata from SQLite
    2. Associated extracted pages
    3. Associated conversations and messages
    4. Associated vector store embeddings
    5. Associated cached study results (summary, notes, quiz)
    6. Uploaded PDF file
    """
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    success = document_service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document.",
        )
    return None


@router.get(
    "/{document_id}/pages",
    response_model=List[PageResponse],
    summary="Get extracted pages for a document",
)
def get_document_pages(document_id: str):
    pages = document_service.get_document_pages(document_id)
    if pages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return [
        PageResponse(
            document_id=p.document_id,
            page=p.page,
            text=p.text,
            char_count=p.char_count,
            word_count=p.word_count,
        )
        for p in pages
    ]


@router.get(
    "/{document_id}/chunks",
    response_model=List[ChunkResponse],
    summary="Get retrieval chunks for a document",
)
def get_document_chunks(document_id: str):
    chunks = document_service.get_document_chunks(document_id)
    if chunks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return [
        ChunkResponse(
            document_id=c.document_id,
            chunk_id=c.chunk_id,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            chunk_text=c.chunk_text,
            char_count=c.char_count,
            word_count=c.word_count,
        )
        for c in chunks
    ]


@router.post(
    "/{document_id}/search",
    response_model=SearchResponse,
    summary="Semantic vector retrieval for a document",
)
def search_document_chunks(
    document_id: str,
    request: SearchRequest,
):
    """
    Searches the persistent vector store for chunks relevant to the user query:
    1. Validates that the document exists and is ready.
    2. Embeds the user query.
    3. Retrieves top-K chunks strictly filtered by document_id.
    4. Applies relevance threshold.
    5. Returns ranked chunks with accurate page numbers and similarity scores.
    """
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    if doc.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{document_id}' is not ready for search. Current status: '{doc.status}'.",
        )

    retrieval_data = retrieval_service.retrieve_relevant_chunks(
        document_id=document_id,
        query=request.query,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
    )

    items = [
        SearchResultItem(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            page=r["page"],
            filename=r["filename"],
            text=r["text"],
            score=r["score"],
            metadata=r.get("metadata"),
        )
        for r in retrieval_data.results
    ]

    return SearchResponse(
        document_id=document_id,
        query=request.query,
        relevant_found=retrieval_data.relevant_found,
        results_count=retrieval_data.results_count,
        results=items,
        message=retrieval_data.message,
    )
