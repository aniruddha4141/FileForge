import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from app.indexing.db import db
from app.core.safety import SafetyManager

class Rule:
    def __init__(self, rule_id: str, name: str, category_filter: str = None, 
                 ext_filter: List[str] = None, min_size: int = None, 
                 max_size: int = None, age_days: int = None,
                 action: str = "move", target_pattern: str = ""):
        """
        Defines a single organization rule.
        - category_filter: e.g. "Images", "Documents"
        - ext_filter: e.g. ["png", "jpg"]
        - age_days: match files modified older than X days
        - action: "move", "copy", "delete"
        - target_pattern: e.g. "{target_dir}/{category}/{year}-{month}/{name}"
        """
        self.rule_id = rule_id
        self.name = name
        self.category_filter = category_filter
        self.ext_filter = [e.lower().lstrip('.') for e in ext_filter] if ext_filter else []
        self.min_size = min_size
        self.max_size = max_size
        self.age_days = age_days
        self.action = action  # "move", "copy", "delete"
        self.target_pattern = target_pattern

    def matches(self, file_rec: Dict[str, Any]) -> bool:
        """Checks if a file record matches this rule's filters."""
        # Category filter
        if self.category_filter and file_rec["category"] != self.category_filter:
            return False

        # Extension filter
        if self.ext_filter and file_rec["extension"] not in self.ext_filter:
            return False

        # Size filters
        if self.min_size is not None and file_rec["size"] < self.min_size:
            return False
        if self.max_size is not None and file_rec["size"] > self.max_size:
            return False

        # Age filter (in days since last modified)
        if self.age_days is not None:
            mod_time = file_rec["modified_at"]
            age_seconds = time.time() - mod_time
            age_days_calc = age_seconds / (24 * 3600)
            if age_days_calc < self.age_days:
                return False

        return True

    def evaluate_target(self, file_rec: Dict[str, Any], base_target_dir: str) -> str:
        """Evaluates target file path pattern substituting folder/file tokens."""
        if self.action == "delete":
            return ""

        # Extract path variables
        dt = datetime.fromtimestamp(file_rec["modified_at"])
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        day = dt.strftime("%d")
        category = file_rec["category"]
        ext = file_rec["extension"]
        name = file_rec["name"]
        
        # Substitute pattern strings
        target_rel = self.target_pattern.format(
            category=category,
            ext=ext,
            year=year,
            month=month,
            day=day,
            name=name
        )
        
        target_path = Path(base_target_dir) / target_rel
        return str(target_path.resolve())

class RuleEngine:
    @staticmethod
    def get_default_organize_profile(base_target_dir: str) -> List[Rule]:
        """Returns standard cleanup and sorting rules rules."""
        return [
            Rule(
                "org_docs", "Organize Documents", 
                category_filter="Documents",
                target_pattern="Documents/{name}"
            ),
            Rule(
                "org_images", "Organize Images", 
                category_filter="Images",
                target_pattern="Images/{year}-{month}/{name}"
            ),
            Rule(
                "org_videos", "Organize Videos", 
                category_filter="Videos",
                target_pattern="Videos/{name}"
            ),
            Rule(
                "org_audio", "Organize Audio", 
                category_filter="Audio",
                target_pattern="Audio/{name}"
            ),
            Rule(
                "org_archives", "Organize Archives", 
                category_filter="Archives",
                target_pattern="Archives/{name}"
            ),
            Rule(
                "org_code", "Organize Source Code", 
                category_filter="Source Code",
                target_pattern="SourceCode/{name}"
            )
        ]

    @classmethod
    def simulate_rules(cls, rules: List[Rule], source_dir: str, 
                       base_target_dir: str) -> List[Dict[str, Any]]:
        """
        Simulates file operations based on rules. Returns a list of changes:
        [ { "source": src, "target": tgt, "action": act, "file_rec": rec, "safe": bool }, ... ]
        """
        # Fetch all files currently indexed in the source folder
        files = db.get_files_under_dir(source_dir)
        operations = []
        
        for file_rec in files:
            # Check safety
            src_path = file_rec["path"]
            if not SafetyManager.is_safe_to_modify(src_path):
                continue
                
            for rule in rules:
                if rule.matches(file_rec):
                    target_path = rule.evaluate_target(file_rec, base_target_dir)
                    
                    # Prevent moving file to the exact same location
                    if src_path == target_path:
                        break

                    is_safe = True
                    if target_path and not SafetyManager.is_safe_to_modify(target_path):
                        is_safe = False

                    operations.append({
                        "rule_name": rule.name,
                        "source": src_path,
                        "target": target_path,
                        "action": rule.action,
                        "size": file_rec["size"],
                        "file_rec": file_rec,
                        "is_safe": is_safe
                    })
                    break  # Stop evaluating rules for this file once it matches one
                    
        return operations
