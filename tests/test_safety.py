import unittest
import os
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.safety import SafetyManager
from app.core.config import config

class TestSafetyManager(unittest.TestCase):
    def test_system_critical_folders_blocked(self):
        # Paths that must be protected
        windows_path = "C:\\Windows\\System32\\cmd.exe"
        prog_files = "C:\\Program Files\\Common Files"
        sys_volume = "D:\\System Volume Information"
        
        self.assertFalse(SafetyManager.is_safe_to_modify(windows_path))
        self.assertFalse(SafetyManager.is_safe_to_modify(prog_files))
        self.assertFalse(SafetyManager.is_safe_to_modify(sys_volume))

    def test_drive_roots_blocked(self):
        # Roots of drives must never be deleted
        self.assertFalse(SafetyManager.is_safe_to_modify("C:\\"))
        self.assertFalse(SafetyManager.is_safe_to_modify("D:\\"))
        self.assertFalse(SafetyManager.is_safe_to_modify("/"))

    def test_user_home_blocked(self):
        home_path = str(Path.home().resolve())
        self.assertFalse(SafetyManager.is_safe_to_modify(home_path))
        # Ensure subfolder under home is allowed (e.g., Downloads, Documents)
        self.assertTrue(SafetyManager.is_safe_to_modify(os.path.join(home_path, "Downloads", "test_file.txt")))

    def test_config_folder_blocked(self):
        config_path = str(config.config_dir.resolve())
        self.assertFalse(SafetyManager.is_safe_to_modify(config_path))
        self.assertFalse(SafetyManager.is_safe_to_modify(os.path.join(config_path, "settings.json")))

    def test_safe_paths_allowed(self):
        # Normal folders should be allowed
        temp_test_path = "C:\\Users\\Public\\Documents\\my_file.txt"
        if os.name != 'nt':
            temp_test_path = "/tmp/my_file.txt"
        self.assertTrue(SafetyManager.is_safe_to_modify(temp_test_path))

if __name__ == '__main__':
    unittest.main()
