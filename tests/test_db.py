import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.indexing.db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use a temporary file-based database for testing to preserve tables across connections
        self.db_path = "test_index.db"
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        # Wait slightly for handles to close and remove the test database file
        import gc
        gc.collect()
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass

    def test_schema_initialization(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Verify table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files';")
        self.assertIsNotNone(cursor.fetchone())

        # Verify FTS table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files_fts';")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_batch_insertion_and_fts_triggers(self):
        # Insert mock files
        files = [
            ("C:/test/file1.txt", "file1.txt", "C:/test", 1024, "txt", "text/plain", 1000.0, 2000.0, 3000.0, 0, 0, None, "Documents"),
            ("C:/test/image.png", "image.png", "C:/test", 204850, "png", "image/png", 1000.0, 2000.0, 3000.0, 0, 0, None, "Images"),
            ("C:/test/video.mp4", "video.mp4", "C:/test", 99550302, "mp4", "video/mp4", 1000.0, 2000.0, 3000.0, 0, 0, None, "Videos")
        ]
        
        self.db.insert_files_batch(files)
        
        # Check summary
        summary = self.db.get_scanned_summary()
        self.assertEqual(summary["total_files"], 3)
        self.assertEqual(summary["total_size"], 1024 + 204850 + 99550302)
        self.assertEqual(summary["total_folders"], 1)

        # Verify FTS table was synchronized via triggers
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files_fts;")
        self.assertEqual(cursor.fetchone()[0], 3)
        conn.close()

    def test_search_fts(self):
        files = [
            ("C:/test/reports_2026.pdf", "reports_2026.pdf", "C:/test", 5000, "pdf", "application/pdf", 1000.0, 1000.0, 1000.0, 0, 0, None, "Documents"),
            ("C:/test/dataset.csv", "dataset.csv", "C:/test", 8000, "csv", "text/csv", 1000.0, 1000.0, 1000.0, 0, 0, None, "Documents")
        ]
        self.db.insert_files_batch(files)

        # Search query matching "reports"
        res = self.db.search_fts("reports")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "reports_2026.pdf")

        # Search matching category Documents
        res_cat = self.db.search_fts("", categories=["Documents"])
        self.assertEqual(len(res_cat), 2)

    def test_category_stats(self):
        files = [
            ("C:/test/file1.txt", "file1.txt", "C:/test", 100, "txt", "text/plain", 1000.0, 1000.0, 1000.0, 0, 0, None, "Documents"),
            ("C:/test/file2.txt", "file2.txt", "C:/test", 200, "txt", "text/plain", 1000.0, 1000.0, 1000.0, 0, 0, None, "Documents"),
            ("C:/test/img.png", "img.png", "C:/test", 500, "png", "image/png", 1000.0, 1000.0, 1000.0, 0, 0, None, "Images")
        ]
        self.db.insert_files_batch(files)
        
        stats = self.db.get_category_stats()
        self.assertEqual(len(stats), 2)
        
        # Verify sizes sum
        docs_stat = next(s for s in stats if s["category"] == "Documents")
        self.assertEqual(docs_stat["file_count"], 2)
        self.assertEqual(docs_stat["total_size"], 300)

if __name__ == '__main__':
    unittest.main()
