import time
from typing import List, Dict, Tuple, Any
from app.indexing.db import db
from app.cleanup.operations import FileOperations

class RecoveryRegistry:
    def __init__(self):
        self._init_history_tables()

    def _init_history_tables(self):
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    description TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL, -- 'move', 'copy', 'delete'
                    source TEXT NOT NULL,
                    target TEXT,
                    FOREIGN KEY(session_id) REFERENCES history_sessions(id) ON DELETE CASCADE
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def start_session(self, description: str) -> int:
        """Starts a new operations history session and returns the session ID."""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history_sessions (timestamp, description) VALUES (?, ?);",
                (time.time(), description)
            )
            session_id = cursor.lastrowid
            conn.commit()
            return session_id
        finally:
            conn.close()

    def log_action(self, session_id: int, action_type: str, source: str, target: str = None):
        """Logs an individual file operation under a session."""
        conn = db.get_connection()
        try:
            conn.execute(
                "INSERT INTO history_actions (session_id, action_type, source, target) VALUES (?, ?, ?, ?);",
                (session_id, action_type, source, target)
            )
            conn.commit()
        finally:
            conn.close()

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Returns all logged sessions, newest first."""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history_sessions ORDER BY id DESC;")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_session_actions(self, session_id: int) -> List[Dict[str, Any]]:
        """Returns all individual actions for a specific session."""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history_actions WHERE session_id = ? ORDER BY id DESC;", (session_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def rollback_session(self, session_id: int) -> Tuple[int, int, str]:
        """
        Attempts to reverse all actions in a session.
        Returns (success_count, fail_count, message).
        """
        actions = self.get_session_actions(session_id)
        if not actions:
            return 0, 0, "No actions found for this session."

        success_count = 0
        fail_count = 0
        has_deletes = False

        for action in actions:
            action_type = action["action_type"]
            src = action["source"]
            tgt = action["target"]

            if action_type == "move":
                # Reverse move: target -> source
                if FileOperations.move_file(tgt, src):
                    success_count += 1
                else:
                    fail_count += 1
            elif action_type == "copy":
                # Reverse copy: delete copy target
                # Check target file safety
                if tgt and FileOperations._fallback_delete(tgt):
                    success_count += 1
                else:
                    fail_count += 1
            elif action_type == "delete":
                has_deletes = True
                # We can't reverse delete directly from python (files are in Recycle Bin).
                # The user must restore them from Windows Recycle Bin manually.
                # Mark as skipped / logged
                success_count += 1

        # Delete session from history if successfully rolled back
        if fail_count == 0:
            conn = db.get_connection()
            try:
                conn.execute("DELETE FROM history_sessions WHERE id = ?;", (session_id,))
                conn.commit()
            finally:
                conn.close()

        msg = f"Rollback complete: {success_count} actions reverted."
        if fail_count > 0:
            msg += f" {fail_count} actions failed to revert (files may have been modified or locked)."
        if has_deletes:
            msg += "\n\nNote: Deleted files were sent to the Recycle Bin and must be restored manually from Windows."

        return success_count, fail_count, msg

# Global registry instance
recovery_registry = RecoveryRegistry()
