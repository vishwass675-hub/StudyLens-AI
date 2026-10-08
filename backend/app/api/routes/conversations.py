"""
Conversations and message routes for persistent multi-turn chat sessions.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
)
from backend.app.services.conversation_service import conversation_service
from backend.app.services.document_service import document_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List all persistent conversations",
)
def list_conversations(
    document_id: Optional[str] = Query(None, description="Filter by active document ID")
):
    convs = conversation_service.list_conversations(document_id=document_id)
    return ConversationListResponse(
        conversations=[ConversationResponse(**c) for c in convs]
    )


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
def create_conversation(request: ConversationCreate):
    # Verify that the document exists
    doc = document_service.get_document(request.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{request.document_id}' not found.",
        )

    try:
        conv = conversation_service.create_conversation(
            document_id=request.document_id,
            title=request.title,
        )
        # Fetch full conversation record with document filename
        full = conversation_service.get_conversation(conv["id"])
        return ConversationResponse(**full)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
)
def get_conversation(conversation_id: str):
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return ConversationResponse(**conv)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Rename conversation",
)
def update_conversation_title(
    conversation_id: str,
    request: ConversationUpdate,
):
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    success = conversation_service.update_title(conversation_id, request.title.strip())
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation title.",
        )

    updated = conversation_service.get_conversation(conversation_id)
    return ConversationResponse(**updated)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation and associated messages",
)
def delete_conversation(conversation_id: str):
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    success = conversation_service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation.",
        )
    return None


@router.get(
    "/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="Get messages for a conversation",
)
def get_conversation_messages(conversation_id: str):
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    raw_msgs = conversation_service.get_messages(conversation_id)
    return [MessageResponse(**m) for m in raw_msgs]


@router.post(
    "/{conversation_id}/summarize-title",
    response_model=ConversationResponse,
    summary="Auto-summarize conversation title from chat messages",
)
async def summarize_conversation_title(conversation_id: str):
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    messages = conversation_service.get_messages(conversation_id)
    user_msg = "Overview"
    asst_msg = None
    for m in messages:
        if m.get("role") == "user":
            user_msg = m.get("content", "")
        elif m.get("role") == "assistant" and not asst_msg:
            asst_msg = m.get("content", "")

    await conversation_service.summarize_title_with_ai(
        conversation_id=conversation_id,
        user_message=user_msg,
        assistant_message=asst_msg,
    )
    updated = conversation_service.get_conversation(conversation_id)
    return ConversationResponse(**updated)
