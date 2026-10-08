"""
LLM Academic Tutor module providing grounded, cited question answering using Gemini or OpenAI.
"""

from typing import List, Dict, Any, Optional
import os


ACADEMIC_TUTOR_SYSTEM_PROMPT = """You are StudyLens AI — an expert, articulate, and encouraging academic tutor.
Your mission is to help students deeply comprehend academic textbooks, research papers, lecture notes, and scientific articles.

Instructions:
1. Grounded & Factual: Answer the student's question using the provided context excerpts from the document. Do not fabricate or invent facts outside of the text.
2. Direct Page Citations: Always cite the source page number when discussing findings, theorems, equations, definitions, or statements (e.g., "[Page 4]" or "[Pages 2, 5]").
3. Pedagogical Structure:
   - Provide a direct, clear summary of the answer first.
   - Break down complex methodologies, formulas, or logical steps clearly.
   - Use structured formatting (bullet points, bold highlights, numbered steps) to enhance readability.
4. Document Scope & Honesty: If the provided context does not contain sufficient details to answer the student's question, politely and transparently explain that the information is not present in the retrieved sections of the document, and suggest what related topics are covered.
"""


class LLMTutor:
    """
    Orchestrates grounded question answering with LLM providers (Gemini or OpenAI).
    """

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.provider = provider.lower()
        self.temperature = temperature
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self._gemini_client = None

        if self.provider == "gemini":
            resolved_key = (
                api_key
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )
            if resolved_key:
                self.api_key = resolved_key
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=resolved_key)
                except Exception:
                    pass

            self.model_name = model_name or "gemini-1.5-flash"

        elif self.provider == "openai":
            import openai
            resolved_key = api_key or os.getenv("OPENAI_API_KEY")
            if resolved_key:
                self.client = openai.OpenAI(api_key=resolved_key)
                self.api_key = resolved_key
            else:
                self.client = None
            self.model_name = model_name or "gpt-4o-mini"
        else:
            self.model_name = "mock-tutor"

    def _build_context_prompt(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Constructs the prompt containing retrieved excerpts and the student's question."""
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            page = chunk.get("page_number", "?")
            score = chunk.get("score", 0.0)
            text = chunk.get("text", "").strip()
            block = f"--- [EXCERPT {idx} | Page {page} | Relevance: {int(score * 100)}%] ---\n{text}"
            context_blocks.append(block)

        context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant context found in document."

        prompt = f"""DOCUMENT CONTEXT EXCERPTS:
{context_str}

STUDENT QUESTION:
{question}

Please provide a grounded, educational answer with explicit page citations:"""
        return prompt

    def answer_question(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a grounded academic response to the student's question.

        Returns:
            Dict containing 'answer', 'sources', 'model_name', and 'provider'.
        """
        if not retrieved_chunks:
            return {
                "answer": "I couldn't find any relevant excerpts in the uploaded document to answer this question. Please try rephrasing your question or asking about topics covered in the document.",
                "sources": [],
                "model_name": self.model_name,
                "provider": self.provider,
            }

        prompt = self._build_context_prompt(question, retrieved_chunks)

        if self.provider == "gemini":
            if not self.api_key:
                raise ValueError(
                    "Gemini API key is required. Set GEMINI_API_KEY in .env or enter it in the sidebar."
                )

            # 1. Try google.genai Client first
            if self._gemini_client is not None:
                from google.genai import types
                candidate_models = [self.model_name, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
                for cand in candidate_models:
                    try:
                        resp = self._gemini_client.models.generate_content(
                            model=cand,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=ACADEMIC_TUTOR_SYSTEM_PROMPT,
                                temperature=self.temperature,
                            ),
                        )
                        if resp and resp.text:
                            return {
                                "answer": resp.text,
                                "sources": retrieved_chunks,
                                "model_name": cand,
                                "provider": "gemini",
                            }
                    except Exception as e:
                        print(f"[StudyLens AI] Attempt with {cand} failed: {e}")

            # 2. Try google.generativeai legacy fallback
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                candidate_models = [self.model_name, "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
                last_err = None
                for cand in candidate_models:
                    try:
                        model = genai_legacy.GenerativeModel(
                            model_name=cand,
                            system_instruction=ACADEMIC_TUTOR_SYSTEM_PROMPT,
                            generation_config=genai_legacy.types.GenerationConfig(
                                temperature=self.temperature,
                            ),
                        )
                        resp = model.generate_content(prompt)
                        if resp and resp.text:
                            return {
                                "answer": resp.text,
                                "sources": retrieved_chunks,
                                "model_name": cand,
                                "provider": "gemini",
                            }
                    except Exception as e:
                        last_err = e

                raise RuntimeError(f"Gemini generation error: {str(last_err)}")
            except Exception as e:
                raise RuntimeError(f"Gemini service error: {str(e)}")

        elif self.provider == "openai":
            if not self.client:
                raise ValueError(
                    "OpenAI API key is required. Set OPENAI_API_KEY in .env or enter it in the sidebar."
                )

            messages = [
                {"role": "system", "content": ACADEMIC_TUTOR_SYSTEM_PROMPT},
            ]

            # Append short recent history if provided
            if conversation_history:
                for msg in conversation_history[-4:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": prompt})

            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
            )
            answer_text = resp.choices[0].message.content

            return {
                "answer": answer_text,
                "sources": retrieved_chunks,
                "model_name": self.model_name,
                "provider": "openai",
            }

        else:
            # Fallback mock answer if no API key is configured
            mock_body = f"""**Tutor Summary (Offline Demo Mode)**

Based on the retrieved excerpts from **Page {retrieved_chunks[0].get('page_number', 1)}**:

> *"{retrieved_chunks[0].get('text', '')[:200]}..."*

To generate live AI tutor explanations, please add your **GEMINI_API_KEY** or **OPENAI_API_KEY** in the sidebar or `.env` file.
"""
            return {
                "answer": mock_body,
                "sources": retrieved_chunks,
                "model_name": "offline-preview",
                "provider": "local",
            }
