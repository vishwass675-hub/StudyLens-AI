"""
Pydantic schemas for Study Tools: Summary, Revision Notes, and AI Quiz.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Source Reference
# -----------------------------------------------------------------------------
class ToolSource(BaseModel):
    document: str = Field(..., description="Document filename")
    page: int = Field(..., description="1-indexed source page number")


# -----------------------------------------------------------------------------
# Summary Schemas
# -----------------------------------------------------------------------------
class DefinitionItem(BaseModel):
    term: str = Field(..., description="Key technical term")
    definition: str = Field(..., description="Academic definition from document")


class SummaryRequest(BaseModel):
    force_regenerate: bool = Field(
        default=False, description="Bypass cache and regenerate summary"
    )
    max_topics: Optional[int] = Field(
        default=8, ge=2, le=20, description="Target number of key topics"
    )


class SummaryResponse(BaseModel):
    document_id: str
    document_overview: str
    topics: List[str]
    key_takeaways: List[str]
    key_definitions: List[DefinitionItem] = Field(default_factory=list)
    exam_points: List[str] = Field(default_factory=list)
    sources: List[ToolSource] = Field(default_factory=list)
    cached: bool = False


# -----------------------------------------------------------------------------
# Revision Notes Schemas
# -----------------------------------------------------------------------------
class NoteSection(BaseModel):
    heading: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    exam_tip: Optional[str] = None


class NotesRequest(BaseModel):
    force_regenerate: bool = Field(
        default=False, description="Bypass cache and regenerate notes"
    )


class NotesResponse(BaseModel):
    document_id: str
    title: str
    markdown_content: str
    sections: List[NoteSection] = Field(default_factory=list)
    sources: List[ToolSource] = Field(default_factory=list)
    cached: bool = False


# -----------------------------------------------------------------------------
# Quiz Schemas
# -----------------------------------------------------------------------------
class QuizQuestion(BaseModel):
    id: int
    topic: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    page_hint: Optional[int] = None


class QuizRequest(BaseModel):
    num_questions: int = Field(
        default=10, ge=1, le=20, description="Total quiz questions to generate"
    )
    question_type: str = Field(
        default="mcq", description="Question format (mcq, true_false, short_answer)"
    )
    topic: Optional[str] = Field(
        default=None, description="Optional focused topic name"
    )
    force_regenerate: bool = Field(
        default=False, description="Bypass cache and generate new quiz"
    )


class QuizResponse(BaseModel):
    document_id: str
    quiz_id: str
    total_questions: int
    questions: List[QuizQuestion]
    sources: List[ToolSource] = Field(default_factory=list)
    cached: bool = False


# -----------------------------------------------------------------------------
# Quiz Evaluation & Weak Topic Detection Schemas
# -----------------------------------------------------------------------------
class UserAnswerSubmission(BaseModel):
    question_id: int
    user_answer: str
    topic: str


class QuizEvaluationRequest(BaseModel):
    quiz_id: Optional[str] = None
    answers: List[UserAnswerSubmission]
    questions: List[QuizQuestion]


class WeakTopicItem(BaseModel):
    topic: str
    incorrect: int
    total: int
    accuracy_percentage: float


class QuizEvaluationResponse(BaseModel):
    score: int
    total: int
    accuracy_percentage: float
    weak_topics: List[WeakTopicItem]
    recommendations: List[str]
