import os
import time
import queue
import threading
import fnmatch
from pathlib import Path
from typing import List, Set, Dict, Any, Tuple
from PyQt6.QtCore import QThread, pyqtSignal
from app.indexing.db import db
from app.utils.helpers import get_file_category, get_mime_type

class FileScanner(QThread):
    # Signals for UI communication
    progress_updated = pyqtSignal(dict)
    scan_finished = pyqtSignal(dict)
    scan_error = pyqtSignal(str)

    def __init__(self, root_paths: List[str], excluded_patterns: List[str] = None):
        super().__init__()
        self.root_paths = [os.path.abspath(p) for p in root_paths]
        self.excluded_patterns = excluded_patterns or []
        
        # Crawler state flags
        self.is_paused = False
        self.is_cancelled = False
        self.pause_condition = threading.Condition()
        
        # Statistics
        self.files_scanned = 0
        self.folders_scanned = 0
        self.bytes_scanned = 0
        
        # Threading queues
        self.dir_queue = queue.Queue()
        self.write_queue = queue.Queue()
        self.active_threads_count = 0
        self.active_threads_lock = threading.Lock()
        
        # Visit tracking (to prevent infinite loops with cyclic folders)
        self.visited_dirs: Set[str] = set()
        self.visited_lock = threading.Lock()
        
        # Performance settings
        self.num_worker_threads = min(8, os.cpu_count() or 4)

    def check_paused(self):
        """Blocks thread execution if pause flag is set."""
        if self.is_paused:
            with self.pause_condition:
                while self.is_paused and not self.is_cancelled:
                    self.pause_condition.wait(0.1)

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
        with self.pause_condition:
            self.pause_condition.notify_all()

    def cancel(self):
        self.is_cancelled = True
        self.resume()  # Unblock if paused

    def is_excluded(self, path: str) -> bool:
        """Checks if a path matches any exclusion patterns."""
        name = os.path.basename(path)
        for pattern in self.excluded_patterns:
            # Absolute matching
            if os.path.isabs(pattern):
                if fnmatch.fnmatch(path.lower(), pattern.lower()):
                    return True
            # Glob / relative matching
            else:
                if fnmatch.fnmatch(name.lower(), pattern.lower()) or \
                   fnmatch.fnmatch(path.lower(), f"*/{pattern.lower()}*"):
                    return True
        return False

    def run(self):
        try:
            self.files_scanned = 0
            self.folders_scanned = 0
            self.bytes_scanned = 0
            self.visited_dirs.clear()
            
            # Reset queues
            self.dir_queue = queue.Queue()
            self.write_queue = queue.Queue()
            
            # Prime the queue with root paths
            for path in self.root_paths:
                if os.path.exists(path) and not self.is_excluded(path):
                    self.dir_queue.put(path)
                    self.visited_dirs.add(path)

            if self.dir_queue.empty():
                self.scan_error.emit("No valid root paths found to scan.")
                return

            start_time = time.time()
            
            # Start database batch-writer thread
            writer_thread = threading.Thread(target=self._db_writer_run, name="FF-DBWriter")
            writer_thread.daemon = True
            writer_thread.start()

            # Start folder-scrawling worker threads
            workers = []
            for i in range(self.num_worker_threads):
                t = threading.Thread(target=self._crawler_worker_run, name=f"FF-Scraper-{i}")
                t.daemon = True
                workers.append(t)
                t.start()

            # UI Update Loop (Throttled update sender)
            last_ui_update = time.time()
            current_dir_display = ""
            
            while True:
                self.check_paused()
                if self.is_cancelled:
                    break
                
                # Check if all workers are idle and the queue is empty
                with self.active_threads_lock:
                    if self.active_threads_count == 0 and self.dir_queue.empty():
                        break
                
                # Periodically push stats to the UI thread (every 100ms)
                now = time.time()
                if now - last_ui_update > 0.1:
                    elapsed = now - start_time
                    speed = self.files_scanned / max(0.1, elapsed)
                    
                    self.progress_updated.emit({
                        "files_scanned": self.files_scanned,
                        "folders_scanned": self.folders_scanned,
                        "bytes_scanned": self.bytes_scanned,
                        "speed": speed,
                        "elapsed": elapsed,
                        "status": "Scanning"
                    })
                    last_ui_update = now
                
                time.sleep(0.05)

            # Signal worker threads and database writer to terminate
            # Workers exit naturally when queue is empty and active_threads == 0
            for t in workers:
                t.join(timeout=1.0)
                
            # Sentinel to DB Writer to commit remaining and exit
            self.write_queue.put(None)
            writer_thread.join(timeout=2.0)

            # Final progress update
            elapsed_total = time.time() - start_time
            self.progress_updated.emit({
                "files_scanned": self.files_scanned,
                "folders_scanned": self.folders_scanned,
                "bytes_scanned": self.bytes_scanned,
                "speed": self.files_scanned / max(0.1, elapsed_total),
                "elapsed": elapsed_total,
                "status": "Finished" if not self.is_cancelled else "Cancelled"
            })

            # Fetch DB summary
            summary = db.get_scanned_summary()
            summary["elapsed"] = elapsed_total
            summary["is_cancelled"] = self.is_cancelled
            self.scan_finished.emit(summary)

        except Exception as e:
            self.scan_error.emit(str(e))

    def _crawler_worker_run(self):
        """Worker thread loop to traverse directories."""
        while not self.is_cancelled:
            self.check_paused()
            
            try:
                # Try to get a directory. Use timeout to periodically check is_cancelled/is_paused
                dir_path = self.dir_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # Mark thread as busy
            with self.active_threads_lock:
                self.active_threads_count += 1

            try:
                self._scan_directory(dir_path)
            except Exception as e:
                print(f"Error scanning {dir_path}: {e}")
            finally:
                self.dir_queue.task_done()
                with self.active_threads_lock:
                    self.active_threads_count -= 1

    def _scan_directory(self, dir_path: str):
        """Scans a single directory, pushing files to DB queue and child dirs to crawl queue."""
        file_records = []
        try:
            # os.scandir returns cached file sizes/mtimes, avoiding extra win32 file stats queries
            with os.scandir(dir_path) as it:
                for entry in it:
                    if self.is_cancelled:
                        return
                    self.check_paused()

                    entry_path = entry.path
                    
                    if self.is_excluded(entry_path):
                        continue

                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        # Skip if we get error resolving symlink or reading file status
                        continue

                    if is_dir:
                        # Prevent duplicate traversal and infinite symlink loops
                        with self.visited_lock:
                            if entry_path not in self.visited_dirs:
                                self.visited_dirs.add(entry_path)
                                self.dir_queue.put(entry_path)
                    else:
                        try:
                            stat = entry.stat()
                            size = stat.st_size
                            
                            # Standard timestamps
                            created_at = stat.st_ctime
                            modified_at = stat.st_mtime
                            accessed_at = stat.st_atime
                            
                            # Hidden / System attributes (Windows specific check)
                            is_hidden = 0
                            is_system = 0
                            if os.name == 'nt':
                                import win32file
                                attrs = win32file.GetFileAttributes(entry_path)
                                is_hidden = 1 if attrs & 2 else 0  # FILE_ATTRIBUTE_HIDDEN
                                is_system = 1 if attrs & 4 else 0  # FILE_ATTRIBUTE_SYSTEM
                            else:
                                if entry.name.startswith('.'):
                                    is_hidden = 1

                            ext = os.path.splitext(entry.name)[1].lower().lstrip('.')
                            mime = get_mime_type(entry_path)
                            category = get_file_category(entry_path)

                            # Record matching columns for SQLite batch insertion
                            record = (
                                entry_path,
                                entry.name,
                                dir_path,
                                size,
                                ext,
                                mime,
                                created_at,
                                modified_at,
                                accessed_at,
                                is_hidden,
                                is_system,
                                None,  # Hash computed on-demand later
                                category
                            )
                            file_records.append(record)
                            
                            # Increment volatile stats counter
                            self.files_scanned += 1
                            self.bytes_scanned += size
                            
                        except (OSError, PermissionError) as e:
                            # Skip if file was deleted during crawl or is lock protected
                            continue

            # Queue batch files records for the writer thread
            if file_records:
                self.write_queue.put(file_records)
                
            # Increment folder count safely
            self.folders_scanned += 1

        except (PermissionError, FileNotFoundError, OSError) as e:
            # Safe recovery from permissions or network disconnects
            pass

    def _db_writer_run(self):
        """Worker thread that executes batch database insertions sequentially."""
        batch_records = []
        last_commit = time.time()
        
        while True:
            try:
                # Wait for file records to insert. Timeout allows periodic flush
                records = self.write_queue.get(timeout=0.1)
                
                # Check for exit sentinel
                if records is None:
                    if batch_records:
                        db.insert_files_batch(batch_records)
                    break
                    
                batch_records.extend(records)
                
                # Flush batch records if batch limit reached (1000 records) or timeout exceeded (500ms)
                if len(batch_records) >= 1000 or (time.time() - last_commit > 0.5 and batch_records):
                    db.insert_files_batch(batch_records)
                    batch_records.clear()
                    last_commit = time.time()
                    
                self.write_queue.task_done()
                
            except queue.Empty:
                if batch_records and time.time() - last_commit > 0.5:
                    db.insert_files_batch(batch_records)
                    batch_records.clear()
                    last_commit = time.time()
                continue
            except Exception as e:
                print(f"Database batch writer thread failed: {e}")
                if batch_records:
                    try:
                        db.insert_files_batch(batch_records)
                    except Exception:
                        pass
                    batch_records.clear()
                # Clean up current item
                try:
                    self.write_queue.task_done()
                except Exception:
                    pass
