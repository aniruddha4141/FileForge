import os
import time
import queue
import threading
from typing import List, Dict, Tuple, Any
from PyQt6.QtCore import QThread, pyqtSignal
from app.indexing.db import db

# Import xxhash with fallback to hashlib MD5
try:
    import xxhash
    def get_hasher():
        return xxhash.xxh64()
    HASHER_NAME = "xxhash_64"
except ImportError:
    import hashlib
    def get_hasher():
        return hashlib.md5()
    HASHER_NAME = "md5"

class DuplicateFinder(QThread):
    # Signals for UI notifications
    progress_updated = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, min_size: int = 1024):
        super().__init__()
        self.min_size = min_size
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def calculate_header_hash(self, path: str) -> str:
        """Calculates the hash of the first 8KB of a file."""
        hasher = get_hasher()
        try:
            with open(path, "rb") as f:
                chunk = f.read(8192)  # Read 8 KB
                hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, PermissionError):
            return ""

    def calculate_full_hash(self, path: str, on_progress_chunk: Any = None) -> str:
        """Calculates the full hash of a file, reading in 64KB chunks."""
        hasher = get_hasher()
        try:
            with open(path, "rb") as f:
                while True:
                    if self.is_cancelled:
                        return ""
                    chunk = f.read(65536)  # 64 KB chunks
                    if not chunk:
                        break
                    hasher.update(chunk)
                    if on_progress_chunk:
                        on_progress_chunk(len(chunk))
            return hasher.hexdigest()
        except (OSError, PermissionError):
            return ""

    def run(self):
        try:
            start_time = time.time()
            self.progress_updated.emit({
                "status": "Screening files by size...",
                "processed": 0,
                "total": 0,
                "percent": 0
            })

            # Phase 1: Retrieve all file sizes with count > 1 (potential duplicates)
            duplicate_sizes = db.get_duplicate_size_groups(self.min_size)
            if not duplicate_sizes or self.is_cancelled:
                self.finished.emit({})
                return

            # Group files by size
            size_groups: Dict[int, List[Dict[str, Any]]] = {}
            total_candidate_files = 0
            
            for size in duplicate_sizes:
                if self.is_cancelled:
                    return
                files = db.get_files_by_size(size)
                if len(files) > 1:
                    size_groups[size] = files
                    total_candidate_files += len(files)

            if total_candidate_files == 0:
                self.finished.emit({})
                return

            self.progress_updated.emit({
                "status": f"Found {len(size_groups)} size groups containing {total_candidate_files} candidates. Pre-screening headers...",
                "processed": 0,
                "total": total_candidate_files,
                "percent": 0
            })

            # Phase 2: Compute 8KB header hash to filter out false positives quickly
            header_hash_groups: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
            processed_candidates = 0
            last_ui_update = time.time()

            for size, files in size_groups.items():
                for file_rec in files:
                    if self.is_cancelled:
                        return
                        
                    path = file_rec["path"]
                    header_hash = self.calculate_header_hash(path)
                    
                    if header_hash:
                        key = (size, header_hash)
                        if key not in header_hash_groups:
                            header_hash_groups[key] = []
                        header_hash_groups[key].append(file_rec)
                        
                    processed_candidates += 1
                    
                    now = time.time()
                    if now - last_ui_update > 0.1:
                        percent = int((processed_candidates / total_candidate_files) * 100)
                        self.progress_updated.emit({
                            "status": f"Pre-screening headers: {processed_candidates}/{total_candidate_files} files",
                            "processed": processed_candidates,
                            "total": total_candidate_files,
                            "percent": percent
                        })
                        last_ui_update = now

            # Clean up header hash groups: keep groups with count > 1
            candidate_hash_groups = {k: v for k, v in header_hash_groups.items() if len(v) > 1}
            total_hashing_candidates = sum(len(files) for files in candidate_hash_groups.values())
            
            if total_hashing_candidates == 0 or self.is_cancelled:
                self.finished.emit({})
                return

            self.progress_updated.emit({
                "status": f"Header filter complete. {total_hashing_candidates} candidate files require full content hashing.",
                "processed": 0,
                "total": total_hashing_candidates,
                "percent": 0
            })

            # Phase 3: Compute full file hash for remaining files, caching to database
            final_duplicate_groups: Dict[str, List[Dict[str, Any]]] = {}
            hashed_files_count = 0
            bytes_hashed = 0
            hashing_start_time = time.time()

            # Helper for tracking bytes hashed
            def add_bytes(num_bytes):
                nonlocal bytes_hashed
                bytes_hashed += num_bytes

            for key, files in candidate_hash_groups.items():
                group_hash_map: Dict[str, List[Dict[str, Any]]] = {}
                
                for file_rec in files:
                    if self.is_cancelled:
                        return
                        
                    path = file_rec["path"]
                    full_hash = file_rec.get("hash")
                    
                    # If not already cached in DB, compute it
                    if not full_hash:
                        full_hash = self.calculate_full_hash(path, on_progress_chunk=add_bytes)
                        if full_hash:
                            # Save in DB cache
                            db.update_file_hash(path, full_hash)
                            
                    if full_hash:
                        if full_hash not in group_hash_map:
                            group_hash_map[full_hash] = []
                        group_hash_map[full_hash].append(file_rec)
                        
                    hashed_files_count += 1
                    
                    now = time.time()
                    if now - last_ui_update > 0.1:
                        elapsed = now - hashing_start_time
                        speed = bytes_hashed / max(0.1, elapsed)  # bytes/sec
                        speed_mb = speed / (1024 * 1024)
                        percent = int((hashed_files_count / total_hashing_candidates) * 100)
                        
                        self.progress_updated.emit({
                            "status": f"Hashing contents: {hashed_files_count}/{total_hashing_candidates} files ({speed_mb:.1f} MB/s)",
                            "processed": hashed_files_count,
                            "total": total_hashing_candidates,
                            "percent": percent
                        })
                        last_ui_update = now

                # Add subgroups with size > 1 to final duplicates list
                for fh, duplicate_list in group_hash_map.items():
                    if len(duplicate_list) > 1:
                        final_duplicate_groups[fh] = duplicate_list

            # Emit final results
            self.finished.emit(final_duplicate_groups)

        except Exception as e:
            self.error.emit(str(e))
            
# Global helper to auto-clean duplicate groups
def select_duplicate_removals(groups: Dict[str, List[Dict[str, Any]]], criteria: str = "newest") -> List[str]:
    """
    Given duplicates groups, returns a list of paths to delete based on criteria:
    - 'newest': Keep oldest file, delete newer files
    - 'oldest': Keep newest file, delete older files
    - 'path_length': Keep shortest file path, delete longer paths
    """
    paths_to_delete = []
    
    for h, files in groups.items():
        if len(files) <= 1:
            continue
            
        # Sort files based on criteria
        if criteria == "newest":
            # Keep oldest: sort ascending by modification date (oldest first). First is kept.
            sorted_files = sorted(files, key=lambda x: x["modified_at"])
        elif criteria == "oldest":
            # Keep newest: sort descending by modification date (newest first). First is kept.
            sorted_files = sorted(files, key=lambda x: x["modified_at"], reverse=True)
        elif criteria == "path_length":
            # Keep shortest path: sort ascending by path length. First is kept.
            sorted_files = sorted(files, key=lambda x: len(x["path"]))
        else:
            continue
            
        # Add all but the first (which is kept) to the deletion list
        for file_rec in sorted_files[1:]:
            paths_to_delete.append(file_rec["path"])
            
    return paths_to_delete
