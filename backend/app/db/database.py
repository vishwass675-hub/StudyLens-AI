"""
SQLite Database connection and schema migration for StudyLens AI.
Provides persistent storage for documents, pages, conversations, messages, and study results.
"""

from typing import Optional
from pathlib import Path
import sqlite3
import datetime
from backend.app.core.config import settings


def get_utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class DatabaseManager:
    """
    Manages persistent SQLite connection and schema migrations.
    Enforces foreign keys, WAL mode, and thread-safe connections.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys and dict row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_db(self):
        """Initializes tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            # 1. Documents Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    page_count INTEGER NOT NULL DEFAULT 0,
                    total_words INTEGER NOT NULL DEFAULT 0,
                    total_chars INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_docs_updated ON documents(updated_at DESC);"
            )

            # 2. Pages Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pages (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    page_text TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pages_doc_id ON pages(document_id, page_number);"
            )

            # 3. Conversations Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conv_doc_id ON conversations(document_id, updated_at DESC);"
            )

            # 4. Messages Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_msg_conv_id ON messages(conversation_id, created_at ASC);"
            )

            # 5. Study Results Table (Cache for summary, notes, quiz)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_results (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    result_type TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, result_type, config_hash)
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_study_res ON study_results(document_id, result_type);"
            )

            conn.commit()


# Global database manager instance
db_manager = DatabaseManager()
