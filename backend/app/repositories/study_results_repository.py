"""
Study Results Repository for persistent SQLite caching.
Saves and loads generated summaries, notes, and quiz sets.
"""

from typing import Dict, Any, Optional
import json
import uuid
import sqlite3
from backend.app.db.database import db_manager, get_utc_now_iso


class StudyResultsRepository:
    """Manages persistent caching of study tools outputs (summaries, notes, quizzes)."""

    def __init__(self, manager=None):
        self.db = manager or db_manager

    def save_result(
        self,
        document_id: str,
        result_type: str,
        config_hash: str,
        data: Dict[str, Any],
    ) -> None:
        """Saves or updates a study tool result in SQLite."""
        now = get_utc_now_iso()
        res_id = f"res_{uuid.uuid4().hex[:10]}"
        data_json = json.dumps(data)

        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO study_results (
                        id, document_id, result_type, config_hash, data_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(document_id, result_type, config_hash) DO UPDATE SET
                        data_json = excluded.data_json,
                        updated_at = excluded.updated_at;
                    """,
                    (res_id, document_id, result_type, config_hash, data_json, now, now),
                )
                conn.commit()
        except sqlite3.IntegrityError:
            pass

    def get_result(
        self,
        document_id: str,
        result_type: str,
        config_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a cached study tool result if it exists."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT data_json
                FROM study_results
                WHERE document_id = ? AND result_type = ? AND config_hash = ?;
                """,
                (document_id, result_type, config_hash),
            )
            row = cur.fetchone()
            if not row:
                return None

            try:
                return json.loads(row["data_json"])
            except Exception:
                return None

    def delete_for_document(self, document_id: str) -> int:
        """Deletes all cached study results for a document."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM study_results WHERE document_id = ?;", (document_id,)
            )
            conn.commit()
            return cur.rowcount


# Global instance
study_results_repo = StudyResultsRepository()
