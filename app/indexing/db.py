import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Tuple, Any

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            config_dir = Path.home() / ".fileforge"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(config_dir / "index.db")
        else:
            self.db_path = db_path
            
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable write-ahead logging (WAL) for better concurrent performance
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Primary metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent TEXT NOT NULL,
                size INTEGER NOT NULL,
                extension TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                created_at REAL NOT NULL,
                modified_at REAL NOT NULL,
                accessed_at REAL NOT NULL,
                is_hidden INTEGER DEFAULT 0,
                is_system INTEGER DEFAULT 0,
                hash TEXT,
                category TEXT NOT NULL
            );
        """)

        # FTS5 Virtual Table for full-text search indexing
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                path,
                name,
                tokenize="unicode61"
            );
        """)

        # Triggers to keep FTS table in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS after_insert_files AFTER INSERT ON files BEGIN
                INSERT OR REPLACE INTO files_fts(rowid, path, name) VALUES (new.rowid, new.path, new.name);
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS after_update_files AFTER UPDATE ON files BEGIN
                INSERT OR REPLACE INTO files_fts(rowid, path, name) VALUES (new.rowid, new.path, new.name);
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS after_delete_files AFTER DELETE ON files BEGIN
                DELETE FROM files_fts WHERE rowid = old.rowid;
            END;
        """)

        # Create indexes for high performance query resolution
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash);")

        conn.commit()
        conn.close()

    def clear_database(self):
        """Clears all records from the database."""
        conn = self.get_connection()
        try:
            conn.execute("DELETE FROM files;")
            conn.execute("DELETE FROM files_fts;")
            conn.commit()
        finally:
            conn.close()

    def insert_files_batch(self, files: List[Tuple[Any, ...]]):
        """
        Inserts multiple file records in a single transaction.
        Each file tuple must match columns:
        (path, name, parent, size, extension, mime_type, created_at, modified_at, accessed_at, is_hidden, is_system, hash, category)
        """
        conn = self.get_connection()
        try:
            conn.executemany("""
                INSERT OR REPLACE INTO files (
                    path, name, parent, size, extension, mime_type, 
                    created_at, modified_at, accessed_at, is_hidden, is_system, hash, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, files)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_file_hash(self, path: str, file_hash: str):
        conn = self.get_connection()
        try:
            conn.execute("UPDATE files SET hash = ? WHERE path = ?;", (file_hash, path))
            conn.commit()
        finally:
            conn.close()

    def delete_file(self, path: str):
        conn = self.get_connection()
        try:
            conn.execute("DELETE FROM files WHERE path = ?;", (path,))
            conn.commit()
        finally:
            conn.close()

    def delete_subfolders(self, parent_path: str):
        """Deletes a directory and all its recursive children from the index."""
        conn = self.get_connection()
        try:
            # Delete direct path and any paths prefix-matching parent_path/ or parent_path\
            normalized_forward = parent_path.replace("\\", "/") + "/"
            normalized_backward = parent_path.replace("/", "\\") + "\\"
            conn.execute("""
                DELETE FROM files 
                WHERE path = ? 
                   OR path LIKE ? 
                   OR path LIKE ?;
            """, (parent_path, normalized_forward + "%", normalized_backward + "%"))
            conn.commit()
        finally:
            conn.close()

    def get_category_stats(self) -> List[Dict[str, Any]]:
        """Returns the count and total size for each category."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, COUNT(*) as file_count, SUM(size) as total_size 
                FROM files 
                GROUP BY category
                ORDER BY total_size DESC;
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_largest_files(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the largest files indexed."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files ORDER BY size DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_duplicate_size_groups(self, min_size: int = 1024) -> List[int]:
        """Returns file sizes that are shared by more than 1 file (Phase 1 duplicate screening)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT size FROM files 
                WHERE size >= ? 
                GROUP BY size 
                HAVING COUNT(*) > 1;
            """, (min_size,))
            return [row["size"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_files_by_size(self, size: int) -> List[Dict[str, Any]]:
        """Returns all files of a specific size."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE size = ?;", (size,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_scanned_summary(self) -> Dict[str, Any]:
        """Returns total file count, total size, and folder count in the index."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count, SUM(size) as size FROM files;")
            file_stats = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(DISTINCT parent) as folders FROM files;")
            folder_stats = cursor.fetchone()
            
            return {
                "total_files": file_stats["count"] or 0,
                "total_size": file_stats["size"] or 0,
                "total_folders": folder_stats["folders"] or 0
            }
        finally:
            conn.close()

    def get_files_under_dir(self, parent_dir: str) -> List[Dict[str, Any]]:
        """Returns files direct or recursive under a folder."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            normalized_forward = parent_dir.replace("\\", "/") + "/"
            normalized_backward = parent_dir.replace("/", "\\") + "\\"
            cursor.execute("""
                SELECT * FROM files 
                WHERE path LIKE ? 
                   OR path LIKE ? 
                   OR path = ?;
            """, (normalized_forward + "%", normalized_backward + "%", parent_dir))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def search_fts(self, text_query: str, categories: List[str] = None, 
                   min_size: int = None, max_size: int = None, 
                   extension: str = None) -> List[Dict[str, Any]]:
        """
        Uses SQLite FTS5 coupled with metadata filters to find files.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Construct FTS5 match query
            # We match the query text against the name column of files_fts
            query_parts = []
            params = []
            
            # Base query joins files and files_fts using rowid
            sql = "SELECT f.* FROM files f JOIN files_fts fts ON f.rowid = fts.rowid WHERE 1=1"
            
            if text_query.strip():
                # Escape search query and support wildcards
                clean_query = text_query.replace('"', '""')
                # If query doesn't have wildcards, append *
                if not clean_query.endswith('*'):
                    clean_query = f"{clean_query}*"
                sql += " AND files_fts MATCH ?"
                params.append(f'name:"{clean_query}"')

            if categories:
                placeholders = ",".join("?" for _ in categories)
                sql += f" AND f.category IN ({placeholders})"
                params.extend(categories)

            if min_size is not None:
                sql += " AND f.size >= ?"
                params.append(min_size)

            if max_size is not None:
                sql += " AND f.size <= ?"
                params.append(max_size)

            if extension:
                ext = extension.strip().lower().lstrip('.')
                sql += " AND f.extension = ?"
                params.append(ext)

            sql += " ORDER BY f.size DESC LIMIT 200;"
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            # Fallback if FTS syntax is invalid
            print(f"FTS Search failed: {e}. Executing fallback path substring query.")
            # Fallback substring query
            sql = "SELECT * FROM files WHERE name LIKE ? "
            params = [f"%{text_query}%"]
            if categories:
                placeholders = ",".join("?" for _ in categories)
                sql += f" AND category IN ({placeholders})"
                params.extend(categories)
            if min_size is not None:
                sql += " AND size >= ?"
                params.append(min_size)
            if max_size is not None:
                sql += " AND size <= ?"
                params.append(max_size)
            if extension:
                sql += " AND extension = ?"
                params.append(extension.strip().lower().lstrip('.'))
            sql += " ORDER BY size DESC LIMIT 200;"
            
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

db = DatabaseManager()
