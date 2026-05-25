import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.duplicate_detection.finder import select_duplicate_removals

class TestDuplicateFinder(unittest.TestCase):
    def test_select_duplicate_removals_newest(self):
        # Mock duplicates groups data
        # Each group represents files with identical hashes
        groups = {
            "hash_aaa": [
                {"path": "C:/a/old.txt", "size": 100, "modified_at": 1000.0},
                {"path": "C:/b/new.txt", "size": 100, "modified_at": 2000.0},
                {"path": "C:/c/newer.txt", "size": 100, "modified_at": 3000.0}
            ]
        }

        # Preset "newest": Keep oldest, select newer files for deletion
        # Here oldest is old.txt (1000.0). We select new.txt (2000.0) and newer.txt (3000.0)
        removals = select_duplicate_removals(groups, "newest")
        self.assertEqual(len(removals), 2)
        self.assertIn("C:/b/new.txt", removals)
        self.assertIn("C:/c/newer.txt", removals)
        self.assertNotIn("C:/a/old.txt", removals)

    def test_select_duplicate_removals_oldest(self):
        groups = {
            "hash_aaa": [
                {"path": "C:/a/old.txt", "size": 100, "modified_at": 1000.0},
                {"path": "C:/b/new.txt", "size": 100, "modified_at": 2000.0},
                {"path": "C:/c/newer.txt", "size": 100, "modified_at": 3000.0}
            ]
        }

        # Preset "oldest": Keep newest, select older files for deletion
        # Here newest is newer.txt (3000.0). We select old.txt (1000.0) and new.txt (2000.0)
        removals = select_duplicate_removals(groups, "oldest")
        self.assertEqual(len(removals), 2)
        self.assertIn("C:/a/old.txt", removals)
        self.assertIn("C:/b/new.txt", removals)
        self.assertNotIn("C:/c/newer.txt", removals)

    def test_select_duplicate_removals_path_length(self):
        groups = {
            "hash_aaa": [
                {"path": "C:/a/very_long_path_name/file.txt", "size": 100, "modified_at": 1000.0},
                {"path": "C:/file.txt", "size": 100, "modified_at": 2000.0},
                {"path": "C:/a/longer_path/file.txt", "size": 100, "modified_at": 3000.0}
            ]
        }

        # Preset "path_length": Keep shortest path name (C:/file.txt). Select longer paths
        removals = select_duplicate_removals(groups, "path_length")
        self.assertEqual(len(removals), 2)
        self.assertIn("C:/a/very_long_path_name/file.txt", removals)
        self.assertIn("C:/a/longer_path/file.txt", removals)
        self.assertNotIn("C:/file.txt", removals)

if __name__ == '__main__':
    unittest.main()
