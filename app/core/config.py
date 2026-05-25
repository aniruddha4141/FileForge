import os
import json
from pathlib import Path

class Config:
    DEFAULT_SETTINGS = {
        "theme": "dark",  # "dark" or "light"
        "accent_color": "#00f0ff",  # Cyberpunk cyan
        "onboarding_completed": False,
        "excluded_paths": [
            "**/System Volume Information",
            "**/$RECYCLE.BIN",
            "**/.git",
            "**/node_modules",
            "**/__pycache__"
        ],
        "protected_paths": [],  # Additional user-protected directories
        "scan_history": []  # List of paths scanned previously
    }

    def __init__(self):
        # Store in user's home directory under .fileforge
        self.config_dir = Path.home() / ".fileforge"
        self.config_file = self.config_dir / "settings.json"
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge loaded keys to support updates
                    for k, v in data.items():
                        self.settings[k] = v
            else:
                self.save()
        except Exception as e:
            print(f"Error loading configuration: {e}")

    def save(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def add_to_history(self, path):
        history = self.settings.get("scan_history", [])
        if path in history:
            history.remove(path)
        history.insert(0, path)
        self.settings["scan_history"] = history[:10]  # Keep last 10 entries
        self.save()

# Global config instance
config = Config()
