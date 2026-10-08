"""
Study Tools Service for StudyLens AI:
- Hierarchical / Grounded Document Summarization
- Structured Academic Revision Notes
- Grounded MCQ Quiz Generation
- Quiz Evaluation and Weak Topic Detection
- In-memory caching with force-regeneration support
- Resilient JSON parsing and single-retry recovery
"""

import json
import re
import uuid
from typing import List, Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from backend.app.models.document import DocumentStatus
from backend.app.services.document_service import document_service
from backend.app.services.ollama_client import ollama_client, OllamaCloudClient, OllamaCloudError
from backend.app.schemas.study_tools import (
    SummaryResponse,
    DefinitionItem,
    NotesResponse,
    NoteSection,
    QuizResponse,
    QuizQuestion,
    ToolSource,
    UserAnswerSubmission,
    QuizEvaluationResponse,
    WeakTopicItem,
)
from backend.app.repositories.study_results_repository import study_results_repo
from backend.app.core.study_tools_prompts import (
    SUMMARY_SYSTEM_PROMPT,
    build_summary_user_prompt,
    NOTES_SYSTEM_PROMPT,
    build_notes_user_prompt,
    QUIZ_SYSTEM_PROMPT,
    build_quiz_user_prompt,
)

T = TypeVar("T", bound=BaseModel)


class StudyToolError(Exception):
    """Exception raised when an error occurs during study tools execution."""
    pass


class StudyToolsService:
    """
    Orchestrates grounded summary, notes, and quiz generation using Nemotron 3 Nano.
    Enforces strict grounding, structured output parsing, caching, and weak-topic analysis.
    """

    def __init__(self, client: Optional[OllamaCloudClient] = None):
        self.client = client or ollama_client
        self._cache: Dict[str, Any] = {}

    def _get_cache_key(self, document_id: str, tool_name: str, **kwargs) -> str:
        sorted_args = sorted(kwargs.items())
        return f"{document_id}:{tool_name}:{sorted_args}"

    def invalidate_document_cache(self, document_id: str):
        """Removes all cached study tool responses for a specific document."""
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{document_id}:")]
        for k in keys_to_remove:
            del self._cache[k]

    def _extract_sources(self, chunks: List[Dict[str, Any]]) -> List[ToolSource]:
        """Deduces unique (document, page) sources from actual retrieval chunks."""
        seen = set()
        sources = []
        for c in chunks:
            doc_name = c.get("filename", "document.pdf")
            page_num = c.get("page", c.get("page_number", 1))
            key = (doc_name, page_num)
            if key not in seen:
                seen.add(key)
                sources.append(ToolSource(document=doc_name, page=int(page_num)))
        return sources

    def _get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Retrieves and verifies chunks for an active ready document."""
        doc = document_service.get_document(document_id)
        if not doc:
            raise StudyToolError(f"Document with ID '{document_id}' not found.")
        if doc.status != DocumentStatus.READY:
            raise StudyToolError(
                f"Document '{document_id}' is not ready for study tools. Current status: '{doc.status}'."
            )
        chunks = document_service.get_document_chunks(document_id)
        if not chunks:
            raise StudyToolError(f"Document '{document_id}' contains no text chunks.")

        return [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "filename": doc.filename,
                "page": c.page_number,
                "text": c.chunk_text,
            }
            for c in chunks
        ]

    def _clean_json_text(self, raw_text: str) -> str:
        """Strips markdown code blocks, preamble, and postscript from LLM text."""
        text = raw_text.strip()
        # Remove markdown code fences like ```json ... ```
        if "```" in text:
            # Match content between ```json ... ``` or ``` ... ```
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()

        # Find first { or [ and last } or ]
        first_brace = text.find("{")
        first_bracket = text.find("[")
        start = -1
        if first_brace != -1 and first_bracket != -1:
            start = min(first_brace, first_bracket)
        elif first_brace != -1:
            start = first_brace
        elif first_bracket != -1:
            start = first_bracket

        last_brace = text.rfind("}")
        last_bracket = text.rfind("]")
        end = max(last_brace, last_bracket)

        if start != -1 and end != -1 and end >= start:
            text = text[start : end + 1]

        return text

    async def _generate_and_parse_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_cls: Type[T],
    ) -> T:
        """
        Sends request to Nemotron, parses JSON with recovery, and retries once on error.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_response = await self.client.generate_chat_completion(messages)
        cleaned = self._clean_json_text(raw_response)

        try:
            parsed = json.loads(cleaned)
            return schema_cls.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as first_err:
            # Safe recovery attempt: retry once with strict error correction prompt
            recovery_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": raw_response},
                {
                    "role": "user",
                    "content": (
                        f"Your previous response was not valid according to the required schema.\n"
                        f"Error: {str(first_err)}\n"
                        f"Please provide ONLY the raw valid JSON object matching the exact schema."
                    ),
                },
            ]
            try:
                second_response = await self.client.generate_chat_completion(recovery_messages)
                second_cleaned = self._clean_json_text(second_response)
                second_parsed = json.loads(second_cleaned)
                return schema_cls.model_validate(second_parsed)
            except Exception as second_err:
                raise StudyToolError(
                    f"Tutor model returned an invalid structured format: {str(second_err)}"
                )

    # -------------------------------------------------------------------------
    # 1. SUMMARY GENERATION
    # -------------------------------------------------------------------------
    async def generate_summary(
        self,
        document_id: str,
        force_regenerate: bool = False,
        max_topics: int = 8,
    ) -> SummaryResponse:
        cache_key = self._get_cache_key(document_id, "summary", max_topics=max_topics)
        if not force_regenerate:
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                return cached.model_copy(update={"cached": True})
            persisted = study_results_repo.get_result(document_id, "summary", str(max_topics))
            if persisted:
                try:
                    resp = SummaryResponse.model_validate(persisted).model_copy(update={"cached": True})
                    self._cache[cache_key] = resp
                    return resp
                except Exception:
                    pass

        chunks = self._get_document_chunks(document_id)
        sources = self._extract_sources(chunks)

        # For long documents (> 16 chunks), apply hierarchical grouping
        selected_chunks = chunks
        if len(chunks) > 16:
            # Sample evenly across pages to represent the entire document
            stride = max(1, len(chunks) // 16)
            selected_chunks = chunks[::stride][:16]

        user_prompt = build_summary_user_prompt(selected_chunks, max_topics=max_topics)

        # Helper temporary validation model
        class SummaryPayload(BaseModel):
            document_overview: str
            topics: List[str]
            key_takeaways: List[str]
            key_definitions: List[Dict[str, str]] = []
            exam_points: List[str] = []

        try:
            result = await self._generate_and_parse_structured(
                SUMMARY_SYSTEM_PROMPT, user_prompt, SummaryPayload
            )
        except OllamaCloudError as e:
            raise StudyToolError(f"Failed communicating with tutor service: {str(e)}")

        defs = [
            DefinitionItem(term=d.get("term", ""), definition=d.get("definition", ""))
            for d in result.key_definitions
            if d.get("term")
        ]

        response = SummaryResponse(
            document_id=document_id,
            document_overview=result.document_overview,
            topics=result.topics,
            key_takeaways=result.key_takeaways,
            key_definitions=defs,
            exam_points=result.exam_points,
            sources=sources,
            cached=False,
        )

        self._cache[cache_key] = response
        study_results_repo.save_result(
            document_id, "summary", str(max_topics), response.model_dump()
        )
        return response

    # -------------------------------------------------------------------------
    # 2. REVISION NOTES GENERATION
    # -------------------------------------------------------------------------
    async def generate_notes(
        self,
        document_id: str,
        force_regenerate: bool = False,
    ) -> NotesResponse:
        cache_key = self._get_cache_key(document_id, "notes")
        if not force_regenerate:
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                return cached.model_copy(update={"cached": True})
            persisted = study_results_repo.get_result(document_id, "notes", "default")
            if persisted:
                try:
                    resp = NotesResponse.model_validate(persisted).model_copy(update={"cached": True})
                    self._cache[cache_key] = resp
                    return resp
                except Exception:
                    pass

        chunks = self._get_document_chunks(document_id)
        sources = self._extract_sources(chunks)

        selected_chunks = chunks
        if len(chunks) > 16:
            stride = max(1, len(chunks) // 16)
            selected_chunks = chunks[::stride][:16]

        user_prompt = build_notes_user_prompt(selected_chunks)

        class NotesPayload(BaseModel):
            title: str
            markdown_content: str
            sections: List[Dict[str, Any]] = []

        try:
            result = await self._generate_and_parse_structured(
                NOTES_SYSTEM_PROMPT, user_prompt, NotesPayload
            )
        except OllamaCloudError as e:
            raise StudyToolError(f"Failed communicating with tutor service: {str(e)}")

        sections = [
            NoteSection(
                heading=s.get("heading", "Topic"),
                summary=s.get("summary", ""),
                key_points=s.get("key_points", []),
                exam_tip=s.get("exam_tip"),
            )
            for s in result.sections
        ]

        response = NotesResponse(
            document_id=document_id,
            title=result.title,
            markdown_content=result.markdown_content,
            sections=sections,
            sources=sources,
            cached=False,
        )

        self._cache[cache_key] = response
        study_results_repo.save_result(
            document_id, "notes", "default", response.model_dump()
        )
        return response

    # -------------------------------------------------------------------------
    # 3. QUIZ GENERATION
    # -------------------------------------------------------------------------
    async def generate_quiz(
        self,
        document_id: str,
        num_questions: int = 10,
        question_type: str = "mcq",
        topic: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> QuizResponse:
        cache_key = self._get_cache_key(
            document_id, "quiz", num_questions=num_questions, topic=topic
        )
        quiz_config_hash = f"{num_questions}_{topic or 'all'}"
        if not force_regenerate:
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                return cached.model_copy(update={"cached": True})
            persisted = study_results_repo.get_result(document_id, "quiz", quiz_config_hash)
            if persisted:
                try:
                    resp = QuizResponse.model_validate(persisted).model_copy(update={"cached": True})
                    self._cache[cache_key] = resp
                    return resp
                except Exception:
                    pass

        chunks = self._get_document_chunks(document_id)
        sources = self._extract_sources(chunks)

        selected_chunks = chunks
        if len(chunks) > 16:
            stride = max(1, len(chunks) // 16)
            selected_chunks = chunks[::stride][:16]

        user_prompt = build_quiz_user_prompt(
            selected_chunks, num_questions=num_questions, topic=topic
        )

        class QuizPayload(BaseModel):
            questions: List[Dict[str, Any]]

        try:
            result = await self._generate_and_parse_structured(
                QUIZ_SYSTEM_PROMPT, user_prompt, QuizPayload
            )
        except OllamaCloudError as e:
            raise StudyToolError(f"Failed communicating with tutor service: {str(e)}")

        questions: List[QuizQuestion] = []
        for idx, q in enumerate(result.questions, start=1):
            opts = [str(o) for o in q.get("options", [])]
            correct = str(q.get("correct_answer", ""))
            # Ensure correct answer is in options
            if correct not in opts and opts:
                opts.append(correct)

            questions.append(
                QuizQuestion(
                    id=idx,
                    topic=q.get("topic", "General"),
                    question=q.get("question", f"Question {idx}"),
                    options=opts,
                    correct_answer=correct,
                    explanation=q.get("explanation", "Grounded in source document."),
                    page_hint=q.get("page_hint"),
                )
            )

        response = QuizResponse(
            document_id=document_id,
            quiz_id=f"quiz_{uuid.uuid4().hex[:10]}",
            total_questions=len(questions),
            questions=questions,
            sources=sources,
            cached=False,
        )

        self._cache[cache_key] = response
        study_results_repo.save_result(
            document_id, "quiz", quiz_config_hash, response.model_dump()
        )
        return response

    # -------------------------------------------------------------------------
    # 4. QUIZ EVALUATION & WEAK TOPIC DETECTION
    # -------------------------------------------------------------------------
    def evaluate_quiz(
        self,
        answers: List[UserAnswerSubmission],
        questions: List[QuizQuestion],
    ) -> QuizEvaluationResponse:
        """
        Scores user quiz answers, analyzes incorrect questions by topic,
        and derives non-judgmental recommendations for revision.
        """
        question_map = {q.id: q for q in questions}
        score = 0
        total = len(questions)

        topic_stats: Dict[str, Dict[str, int]] = {}

        for ans in answers:
            q = question_map.get(ans.question_id)
            if not q:
                continue

            topic = q.topic or "General"
            if topic not in topic_stats:
                topic_stats[topic] = {"total": 0, "incorrect": 0}
            topic_stats[topic]["total"] += 1

            # Case-insensitive whitespace-stripped check
            is_correct = (
                ans.user_answer.strip().lower() == q.correct_answer.strip().lower()
            )

            if is_correct:
                score += 1
            else:
                topic_stats[topic]["incorrect"] += 1

        accuracy = round((score / max(1, total)) * 100, 1)

        weak_topics: List[WeakTopicItem] = []
        recommendations: List[str] = []

        for t_name, stats in topic_stats.items():
            if stats["incorrect"] > 0:
                t_acc = round(
                    ((stats["total"] - stats["incorrect"]) / stats["total"]) * 100, 1
                )
                weak_topics.append(
                    WeakTopicItem(
                        topic=t_name,
                        incorrect=stats["incorrect"],
                        total=stats["total"],
                        accuracy_percentage=t_acc,
                    )
                )
                recommendations.append(
                    f"Review '{t_name}' ({stats['incorrect']} of {stats['total']} questions missed)."
                )

        # Sort weak topics with most missed questions first
        weak_topics.sort(key=lambda w: w.incorrect, reverse=True)

        if not recommendations and score == total and total > 0:
            recommendations.append("Excellent mastery! All questions answered accurately.")

        return QuizEvaluationResponse(
            score=score,
            total=total,
            accuracy_percentage=accuracy,
            weak_topics=weak_topics,
            recommendations=recommendations,
        )


# Global singleton
study_tools_service = StudyToolsService()
