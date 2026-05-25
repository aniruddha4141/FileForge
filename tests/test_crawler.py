import unittest
import os
import shutil
import tempfile
import time
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.scanning.crawler import FileScanner
from app.indexing.db import db

class TestFileScanner(unittest.TestCase):
    def setUp(self):
        # Create temp folder tree
        self.test_dir = tempfile.mkdtemp()
        db.clear_database()

        # Build mock hierarchy
        self.doc_dir = os.path.join(self.test_dir, "docs")
        self.img_dir = os.path.join(self.test_dir, "images")
        self.exclude_dir = os.path.join(self.test_dir, "node_modules")

        os.makedirs(self.doc_dir, exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)
        os.makedirs(self.exclude_dir, exist_ok=True)

        # Write files
        with open(os.path.join(self.doc_dir, "report.pdf"), "wb") as f:
            f.write(b"a" * 1500)  # 1500 bytes

        with open(os.path.join(self.img_dir, "photo.jpg"), "wb") as f:
            f.write(b"b" * 500000) # ~500 KB

        with open(os.path.join(self.exclude_dir, "package.json"), "wb") as f:
            f.write(b"{}")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_crawler_scanning(self):
        # Setup crawler with exclusions
        exclusions = ["**/node_modules"]
        crawler = FileScanner([self.test_dir], excluded_patterns=exclusions)
        
        # We can run crawler synchronously since it inherits QThread
        # QThread.run is the entry point
        crawler.run()

        # Query database and verify
        summary = db.get_scanned_summary()
        
        # Verify node_modules/package.json was skipped (so count = 2)
        self.assertEqual(summary["total_files"], 2)
        self.assertEqual(summary["total_size"], 1500 + 500000)

        # Verify category classification
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT category FROM files WHERE name = 'report.pdf';")
        self.assertEqual(cursor.fetchone()["category"], "Documents")
        
        cursor.execute("SELECT category FROM files WHERE name = 'photo.jpg';")
        self.assertEqual(cursor.fetchone()["category"], "Images")
        
        # Assert exclusion is not present in db
        cursor.execute("SELECT COUNT(*) FROM files WHERE parent LIKE '%node_modules%';")
        self.assertEqual(cursor.fetchone()[0], 0)
        conn.close()

if __name__ == '__main__':
    unittest.main()
