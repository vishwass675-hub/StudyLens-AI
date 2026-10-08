"""
Conversation and Message Repository for persistent SQLite storage.
Handles chat sessions, history, message persistence, and source linking.
"""

from typing import List, Dict, Any, Optional
import json
from backend.app.db.database import db_manager, get_utc_now_iso


class ConversationRepository:
    """Manages database persistence for conversations and messages."""

    def __init__(self, manager=None):
        self.db = manager or db_manager

    def create_conversation(
        self,
        conversation_id: str,
        document_id: str,
        title: str = "New Conversation",
    ) -> Dict[str, Any]:
        """Creates a new conversation associated with an active document."""
        now = get_utc_now_iso()
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, document_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (conversation_id, document_id, title, now, now),
            )
            conn.commit()

        return {
            "id": conversation_id,
            "document_id": document_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a conversation by ID, including its associated document filename."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT c.id, c.document_id, c.title, c.created_at, c.updated_at,
                       d.filename AS document_filename,
                       COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN documents d ON c.document_id = d.id
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.id = ?
                GROUP BY c.id;
                """,
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            return {
                "id": row["id"],
                "document_id": row["document_id"],
                "document_filename": row["document_filename"] or "Unknown Document",
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"],
            }

    def list_conversations(
        self, document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists conversations optionally filtered by document_id, newest first."""
        query = """
            SELECT c.id, c.document_id, c.title, c.created_at, c.updated_at,
                   d.filename AS document_filename,
                   COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN documents d ON c.document_id = d.id
            LEFT JOIN messages m ON c.id = m.conversation_id
        """
        params = []
        if document_id:
            query += " WHERE c.document_id = ?"
            params.append(document_id)

        query += " GROUP BY c.id ORDER BY c.updated_at DESC;"

        with self.db.get_connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "document_id": r["document_id"],
                    "document_filename": r["document_filename"] or "Unknown Document",
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "message_count": r["message_count"],
                }
                for r in rows
            ]

    def update_title(self, conversation_id: str, title: str) -> bool:
        """Renames a conversation."""
        now = get_utc_now_iso()
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?;",
                (title, now, conversation_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def touch_updated_at(self, conversation_id: str) -> None:
        """Updates conversation timestamp after adding a message."""
        now = get_utc_now_iso()
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?;",
                (now, conversation_id),
            )
            conn.commit()

    def delete_conversation(self, conversation_id: str) -> bool:
        """Deletes a conversation and its messages via cascade."""
        with self.db.get_connection() as conn:
            cur = conn.execute("DELETE FROM conversations WHERE id = ?;", (conversation_id,))
            conn.commit()
            return cur.rowcount > 0

    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Saves a user or assistant message with associated retrieval source metadata."""
        now = get_utc_now_iso()
        sources_json = json.dumps(sources) if sources else None

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (message_id, conversation_id, role, content, sources_json, now),
            )
            # Update parent conversation's updated_at
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?;",
                (now, conversation_id),
            )
            conn.commit()

        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "created_at": now,
        }

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieves messages in chronological order for a conversation."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, conversation_id, role, content, sources_json, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC;
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
            messages = []
            for r in rows:
                sources = []
                if r["sources_json"]:
                    try:
                        sources = json.loads(r["sources_json"])
                    except Exception:
                        sources = []

                messages.append(
                    {
                        "id": r["id"],
                        "conversation_id": r["conversation_id"],
                        "role": r["role"],
                        "content": r["content"],
                        "sources": sources,
                        "created_at": r["created_at"],
                    }
                )
            return messages


# Global instance
conversation_repo = ConversationRepository()
