"""
Chat route for StudyLens AI.
Orchestrates retrieval and grounded Nemotron LLM generation.
"""

from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.chat import TutorChatRequest, TutorChatResponse, SourceReference
from backend.app.services.document_service import document_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.llm_service import llm_tutor_service
from backend.app.services.ollama_client import OllamaCloudError
from backend.app.services.conversation_service import conversation_service
from backend.app.repositories.document_repository import document_repo
from backend.app.models.document import DocumentStatus

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=TutorChatResponse,
    summary="Ask questions grounded in the uploaded document",
)
async def chat_with_tutor(request: TutorChatRequest):
    """
    Complete grounded tutor pipeline:
    1. Identify active document and ensure it is ready.
    2. Validate or initialize persistent conversation session.
    3. Retrieve relevant chunks strictly from active document vector store.
    4. If no relevant chunks meet the threshold, return notice and record turn.
    5. Assemble prompt with tutor mode and bounded conversation history.
    6. Query Nemotron 3 Nano 30B Cloud via Ollama Cloud.
    7. Save user & assistant messages with source references to SQLite.
    8. Return answer with metadata-derived source citations and conversation_id.
    """
    doc = document_service.get_document(request.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{request.document_id}' not found.",
        )

    if doc.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{request.document_id}' is not ready for tutoring. Current status: '{doc.status}'.",
        )

    # Validate or create persistent conversation
    conv_id = request.conversation_id
    if conv_id:
        conv = conversation_service.get_conversation(conv_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with ID '{conv_id}' not found.",
            )
        if conv["document_id"] != request.document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation does not belong to the active document.",
            )
    else:
        # Check if an existing conversation already exists for this document to prevent duplicate chats
        existing = conversation_service.list_conversations(document_id=request.document_id)
        if existing:
            conv_id = existing[0]["id"]
        else:
            created_conv = conversation_service.create_conversation(document_id=request.document_id)
            conv_id = created_conv["id"]

    # Refresh last accessed timestamp
    document_repo.update_last_accessed(request.document_id)

    # 1. Retrieve relevant chunks
    retrieval_data = retrieval_service.retrieve_relevant_chunks(
        document_id=request.document_id,
        query=request.message,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
    )

    # 2. Check relevance
    if not retrieval_data.relevant_found or not retrieval_data.results:
        fallback_answer = "I couldn't find enough information about that in the uploaded document."
        conversation_service.record_turn(
            conversation_id=conv_id,
            user_message=request.message,
            assistant_message=fallback_answer,
            sources=[],
        )
        return TutorChatResponse(
            answer=fallback_answer,
            sources=[],
            conversation_id=conv_id,
        )

    # 3. Format bounded conversation history
    conv_history = [
        {"role": m.role, "content": m.content} for m in (request.conversation or [])
    ]

    # 4. Generate grounded answer with Nemotron
    try:
        response = await llm_tutor_service.generate_grounded_answer(
            question=request.message,
            retrieved_chunks=retrieval_data.results,
            mode=request.mode,
            conversation_history=conv_history,
        )

        sources = [
            SourceReference(document=s["document"], page=s["page"])
            for s in response.get("sources", [])
        ]

        # 5. Persist turn with provenance sources in SQLite
        conversation_service.record_turn(
            conversation_id=conv_id,
            user_message=request.message,
            assistant_message=response["answer"],
            sources=[s.model_dump() for s in sources],
        )

        # 6. Auto-summarize conversation title if generic or new
        await conversation_service.maybe_summarize_title(
            conversation_id=conv_id,
            user_message=request.message,
            assistant_message=response["answer"],
        )

        return TutorChatResponse(
            answer=response["answer"],
            sources=sources,
            conversation_id=conv_id,
        )

    except OllamaCloudError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Tutor generation failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )
