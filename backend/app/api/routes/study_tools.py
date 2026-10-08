"""
Study Tools routes:
- POST /api/documents/{document_id}/summary
- POST /api/documents/{document_id}/notes
- POST /api/documents/{document_id}/quiz
- POST /api/documents/{document_id}/quiz/evaluate
"""

from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.study_tools import (
    SummaryRequest,
    SummaryResponse,
    NotesRequest,
    NotesResponse,
    QuizRequest,
    QuizResponse,
    QuizEvaluationRequest,
    QuizEvaluationResponse,
)
from backend.app.services.study_tools_service import (
    study_tools_service,
    StudyToolError,
)

router = APIRouter(prefix="/documents", tags=["Study Tools"])


@router.post(
    "/{document_id}/summary",
    response_model=SummaryResponse,
    summary="Generate structured academic summary of uploaded document",
)
async def generate_document_summary(
    document_id: str,
    request: SummaryRequest = SummaryRequest(),
):
    try:
        return await study_tools_service.generate_summary(
            document_id=document_id,
            force_regenerate=request.force_regenerate,
            max_topics=request.max_topics or 8,
        )
    except StudyToolError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        if "not ready" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred generating summary: {str(e)}",
        )


@router.post(
    "/{document_id}/notes",
    response_model=NotesResponse,
    summary="Generate structured revision notes from uploaded document",
)
async def generate_revision_notes(
    document_id: str,
    request: NotesRequest = NotesRequest(),
):
    try:
        return await study_tools_service.generate_notes(
            document_id=document_id,
            force_regenerate=request.force_regenerate,
        )
    except StudyToolError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        if "not ready" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred generating revision notes: {str(e)}",
        )


@router.post(
    "/{document_id}/quiz",
    response_model=QuizResponse,
    summary="Generate grounded MCQ quiz from uploaded document",
)
async def generate_document_quiz(
    document_id: str,
    request: QuizRequest = QuizRequest(),
):
    try:
        return await study_tools_service.generate_quiz(
            document_id=document_id,
            num_questions=request.num_questions,
            question_type=request.question_type,
            topic=request.topic,
            force_regenerate=request.force_regenerate,
        )
    except StudyToolError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        if "not ready" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred generating quiz: {str(e)}",
        )


@router.post(
    "/{document_id}/quiz/evaluate",
    response_model=QuizEvaluationResponse,
    summary="Evaluate quiz submissions and detect weak topics for revision",
)
def evaluate_quiz_submission(
    document_id: str,
    request: QuizEvaluationRequest,
):
    return study_tools_service.evaluate_quiz(
        answers=request.answers,
        questions=request.questions,
    )
