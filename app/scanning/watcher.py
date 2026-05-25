import os
import threading
from typing import List, Callable
from PyQt6.QtCore import QThread, pyqtSignal
from app.indexing.db import db
from app.utils.helpers import get_file_category, get_mime_type

class DirectoryWatcher(QThread):
    # Signals for UI notifications
    file_created = pyqtSignal(str)
    file_deleted = pyqtSignal(str)
    file_modified = pyqtSignal(str)
    file_renamed = pyqtSignal(str, str)  # old_path, new_path

    def __init__(self, watch_paths: List[str]):
        super().__init__()
        self.watch_paths = [os.path.abspath(p) for p in watch_paths]
        self.is_running = True
        self._threads = []
        self._handles = []

    def run(self):
        """Starts a background monitor thread for each watched path."""
        if os.name != 'nt':
            # Fallback for non-Windows (NOP or simple polling could be added,
            # but Windows is the target OS platform)
            return

        import win32file
        import win32con

        for path in self.watch_paths:
            if not os.path.exists(path):
                continue
                
            t = threading.Thread(
                target=self._watch_directory_run, 
                args=(path,), 
                name=f"FF-Watcher-{os.path.basename(path)}"
            )
            t.daemon = True
            self._threads.append(t)
            t.start()

        # Keep the QThread alive
        while self.is_running:
            self.msleep(100)

    def stop(self):
        self.is_running = False
        # Close handles to force ReadDirectoryChangesW to unblock and throw exception
        import win32file
        for h in self._handles:
            try:
                win32file.CloseHandle(h)
            except Exception:
                pass
        self._handles.clear()
        
        for t in self._threads:
            t.join(timeout=0.2)

    def _watch_directory_run(self, dir_path: str):
        """Windows ReadDirectoryChangesW listener loop."""
        import win32file
        import win32con

        # Open folder directory handle
        try:
            hDir = win32file.CreateFile(
                dir_path,
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_BACKUP_SEMANTICS,
                None
            )
            self._handles.append(hDir)
        except Exception as e:
            print(f"Failed to open watch handle on {dir_path}: {e}")
            return

        # Listen flags
        FILE_NOTIFY_CHANGE_FILE_NAME = win32con.FILE_NOTIFY_CHANGE_FILE_NAME
        FILE_NOTIFY_CHANGE_DIR_NAME = win32con.FILE_NOTIFY_CHANGE_DIR_NAME
        FILE_NOTIFY_CHANGE_SIZE = win32con.FILE_NOTIFY_CHANGE_SIZE
        FILE_NOTIFY_CHANGE_LAST_WRITE = win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
        
        # ReadDirectoryChangesW buffer size (64KB is optimal)
        buf = bytearray(65536)
        
        # Keep track of last rename source path
        last_rename_source = None

        while self.is_running:
            try:
                # Synchronous blocking call (blocks worker thread, not the GUI)
                results = win32file.ReadDirectoryChangesW(
                    hDir,
                    buf,
                    True,  # Watch subtree recursively
                    FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_DIR_NAME | FILE_NOTIFY_CHANGE_SIZE | FILE_NOTIFY_CHANGE_LAST_WRITE,
                    None,
                    None
                )
                
                for action, filename in results:
                    full_path = os.path.join(dir_path, filename)
                    
                    if action == 1:  # File added / Created
                        self._handle_created(full_path)
                    elif action == 2:  # File deleted
                        self._handle_deleted(full_path)
                    elif action == 3:  # File modified / Size or Write Change
                        self._handle_modified(full_path)
                    elif action == 4:  # Rename source (Old name)
                        last_rename_source = full_path
                    elif action == 5:  # Rename target (New name)
                        if last_rename_source:
                            self._handle_renamed(last_rename_source, full_path)
                            last_rename_source = None
                            
            except Exception as e:
                # Will throw exception when CloseHandle is called on stop() or directory deleted
                break

    def _handle_created(self, path: str):
        if not os.path.exists(path) or os.path.isdir(path):
            return
        
        try:
            stat = os.stat(path)
            ext = os.path.splitext(path)[1].lower().lstrip('.')
            category = get_file_category(path)
            mime = get_mime_type(path)
            
            record = (
                path,
                os.path.basename(path),
                os.path.dirname(path),
                stat.st_size,
                ext,
                mime,
                stat.st_ctime,
                stat.st_mtime,
                stat.st_atime,
                0, 0, None, category
            )
            # Insert file record to index cache
            db.insert_files_batch([record])
            self.file_created.emit(path)
        except Exception:
            pass

    def _handle_deleted(self, path: str):
        try:
            # Check if directory or file deleted
            db.delete_file(path)
            db.delete_subfolders(path)  # Delete children in case it was a directory
            self.file_deleted.emit(path)
        except Exception:
            pass

    def _handle_modified(self, path: str):
        if not os.path.exists(path) or os.path.isdir(path):
            return
            
        try:
            stat = os.stat(path)
            ext = os.path.splitext(path)[1].lower().lstrip('.')
            category = get_file_category(path)
            mime = get_mime_type(path)
            
            record = (
                path,
                os.path.basename(path),
                os.path.dirname(path),
                stat.st_size,
                ext,
                mime,
                stat.st_ctime,
                stat.st_mtime,
                stat.st_atime,
                0, 0, None, category  # Hash is cleared on modifications
            )
            db.insert_files_batch([record])
            self.file_modified.emit(path)
        except Exception:
            pass

    def _handle_renamed(self, old_path: str, new_path: str):
        try:
            # Delete old file/subfolder entries
            db.delete_file(old_path)
            db.delete_subfolders(old_path)
            
            # Re-index new path
            if os.path.exists(new_path):
                if os.path.isdir(new_path):
                    # For renamed directories, re-index children since paths changed recursively
                    # In this case, we can just trigger a background crawl update or let it lazy re-crawl.
                    # As a simpler approach: remove children and re-create them.
                    pass
                else:
                    self._handle_created(new_path)
                    
            self.file_renamed.emit(old_path, new_path)
        except Exception:
            pass
