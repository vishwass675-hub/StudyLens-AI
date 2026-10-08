"""
Conversation service for managing persistent chat sessions and message provenance.
Generates concise automatic titles from initial questions and enforces document isolation.
"""

import re
import uuid
from typing import List, Dict, Any, Optional

from backend.app.repositories.conversation_repository import (
    ConversationRepository,
    conversation_repo,
)
from backend.app.repositories.document_repository import (
    DocumentRepository,
    document_repo,
)


class ConversationService:
    """Business logic for persistent multi-turn conversations and message provenance."""

    def __init__(
        self,
        c_repo: Optional[ConversationRepository] = None,
        d_repo: Optional[DocumentRepository] = None,
    ):
        self.conv_repo = c_repo or conversation_repo
        self.doc_repo = d_repo or document_repo

    def generate_title(self, question: str, doc_name: Optional[str] = None) -> str:
        """
        Generates a short, readable title from the question, with intelligent fallback.
        e.g. 'What is third normal form?' -> 'Third Normal Form'
        """
        cleaned = question.strip()
        # Remove common introductory question phrases and conversational filler
        patterns = [
            r"^(what\s+is\s+|what\s+are\s+)",
            r"^(explain\s+|can\s+you\s+explain\s+)",
            r"^(how\s+does\s+|how\s+to\s+)",
            r"^(tell\s+me\s+about\s+)",
            r"^(why\s+is\s+|why\s+do\s+)",
            r"^(describe\s+|summarize\s+)",
            r"^(define\s+)",
            r"^(help\s+me\s+out\s+with\s+|help\s+me\s+with\s+)",
            r"^(can\s+you\s+help\s+me\s+with\s+|please\s+help\s+me\s+with\s+)",
        ]
        for p in patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # Remove trailing punctuation
        cleaned = cleaned.rstrip("?.!").strip()

        # Check for generic/slang conversational filler that doesn't state a topic
        generic_phrases = {
            "this about", "this", "it about", "it", "about", "hello", "hi", "hey",
            "help me out", "help me", "help", "bro i am cooked", "bro i am soo cooked",
            "i am cooked", "cooked", "save me", "help me pass", "teach me this", "explain",
            "overview", "summary"
        }

        if not cleaned or cleaned.lower() in generic_phrases:
            if doc_name:
                cleaned_doc = re.sub(r"^\d+[-_]", "", doc_name).rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
                return f"{cleaned_doc} Overview"
            return "Document Overview"

        # Truncate to maximum 35 characters cleanly at word boundary
        if len(cleaned) > 35:
            truncated = cleaned[:35].rsplit(" ", 1)[0]
            cleaned = truncated if truncated else cleaned[:35]

        # Capitalize title
        return cleaned.title()

    async def summarize_title_with_ai(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: Optional[str] = None,
    ) -> str:
        """
        Uses Nemotron 3 Nano via Ollama Cloud to summarize what the student texted in chat
        into a concise 2 to 5 word conversation title.
        """
        conv = self.conv_repo.get_conversation(conversation_id)
        doc_name = ""
        if conv and conv.get("document_id"):
            doc = self.doc_repo.get_document(conv["document_id"])
            if doc:
                raw_name = getattr(doc, "filename", None) or (doc.get("filename") if isinstance(doc, dict) else "")
                if raw_name:
                    doc_name = re.sub(r"^\d+[-_]", "", raw_name).rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        prompt = (
            "You are an expert conversation title generator for a student study workspace.\n"
            f"Document Topic: {doc_name or 'Uploaded Material'}\n"
            f"Student Message: {user_message}\n"
        )
        if assistant_message:
            prompt += f"Tutor Explanation Snippet: {assistant_message[:200]}\n"

        prompt += (
            "\nTask: Summarize what the student texted in chat into a clean, descriptive title of 2 to 5 words.\n"
            "Rules:\n"
            "- Exactly 2 to 5 words summarizing the core topic.\n"
            "- Title Case (capitalize principal words).\n"
            "- Output ONLY the title text, nothing else.\n"
            "- Do NOT use quotes, emojis, or punctuation.\n"
            "- NEVER use generic phrases like 'Help Me Out', 'Cooked', 'Chat', or 'New Conversation'.\n"
        )

        try:
            from backend.app.services.ollama_client import ollama_client
            raw_title = await ollama_client.generate_chat_completion([
                {"role": "user", "content": prompt}
            ])
            cleaned = raw_title.strip().strip("\"'").rstrip(".!?:")
            cleaned = re.sub(r"^(title|summary|chat title):\s*", "", cleaned, flags=re.IGNORECASE).strip()
            words = cleaned.split()
            if 2 <= len(words) <= 6:
                final_title = " ".join(words[:5]).title()
                self.conv_repo.update_title(conversation_id, final_title)
                return final_title
        except Exception:
            pass

        # Fallback to heuristic
        fallback = self.generate_title(user_message, doc_name=doc_name)
        self.conv_repo.update_title(conversation_id, fallback)
        return fallback

    async def maybe_summarize_title(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: Optional[str] = None,
    ) -> str:
        """
        Auto-summarizes conversation title if the title is generic, default, or within the first 2 turns.
        """
        conv = self.conv_repo.get_conversation(conversation_id)
        if not conv:
            return ""

        current_title = (conv.get("title") or "").strip().lower()
        generic_titles = {
            "new conversation",
            "new chat",
            "help me out",
            "help me",
            "help",
            "bro i am cooked",
            "bro i am soo cooked",
            "cooked",
            "document overview",
            "untitled chat",
        }

        messages = self.conv_repo.get_messages(conversation_id)
        if current_title in generic_titles or len(messages) <= 4:
            return await self.summarize_title_with_ai(
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_message=assistant_message,
            )

        return conv.get("title") or "Study Chat"

    def create_conversation(
        self, document_id: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a conversation verified against an existing document."""
        doc = self.doc_repo.get_document(document_id)
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        final_title = title or "New Conversation"
        return self.conv_repo.create_conversation(
            conversation_id=conv_id,
            document_id=document_id,
            title=final_title,
        )

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves conversation details."""
        return self.conv_repo.get_conversation(conversation_id)

    def list_conversations(
        self, document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists conversations sorted newest first."""
        return self.conv_repo.list_conversations(document_id)

    def update_title(self, conversation_id: str, title: str) -> bool:
        """Renames a conversation."""
        return self.conv_repo.update_title(conversation_id, title)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Deletes a conversation and its messages."""
        return self.conv_repo.delete_conversation(conversation_id)

    def record_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Saves both user and assistant messages for a completed turn.
        If the conversation is titled 'New Conversation', auto-renames based on user question.
        """
        conv = self.conv_repo.get_conversation(conversation_id)
        if not conv:
            return

        # 1. Save user message
        user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        self.conv_repo.add_message(
            message_id=user_msg_id,
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # 2. Save assistant message
        asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        self.conv_repo.add_message(
            message_id=asst_msg_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_message,
            sources=sources,
        )

        # 3. Check if default title should be replaced
        if conv["title"] in ("New Conversation", "New Chat") or not conv["title"]:
            new_title = self.generate_title(user_message)
            self.conv_repo.update_title(conversation_id, new_title)

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieves messages for a conversation."""
        return self.conv_repo.get_messages(conversation_id)


# Global instance
conversation_service = ConversationService()
