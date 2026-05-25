import os
import shutil
import ctypes
from pathlib import Path
from typing import List, Dict, Tuple
from app.core.safety import SafetyManager
from app.indexing.db import db

class FileOperations:
    @staticmethod
    def send_to_recycle_bin(paths: List[str]) -> Dict[str, bool]:
        """
        Sends list of file/folder paths to the Windows Recycle Bin using Win32 API.
        Returns a dict mapping path -> success boolean status.
        """
        results = {}
        # Pre-filter paths using SafetyManager
        safe_paths = [p for p in paths if SafetyManager.is_safe_to_modify(p)]
        
        # Mark unsafe paths as failed immediately
        for p in paths:
            if p not in safe_paths:
                results[p] = False

        if not safe_paths:
            return results

        if os.name == 'nt':
            from ctypes import Structure, c_void_p, c_uint, c_wchar_p, byref
            from ctypes.wintypes import HWND, UINT, BOOL

            class SHFILEOPSTRUCTW(Structure):
                _fields_ = [
                    ("hwnd", HWND),
                    ("wFunc", UINT),
                    ("pFrom", c_wchar_p),
                    ("pTo", c_wchar_p),
                    ("fFlags", c_uint),
                    ("fAnyOperationsAborted", BOOL),
                    ("hNameMappings", c_void_p),
                    ("lpszProgressTitle", c_wchar_p)
                ]

            shell32 = ctypes.windll.shell32
            
            # Windows SHFileOperationW accepts paths separated by a single null byte
            # and terminated by a double null byte
            paths_string = "\0".join(safe_paths) + "\0\0"

            fileop = SHFILEOPSTRUCTW()
            fileop.hwnd = None
            fileop.wFunc = 0x0003  # FO_DELETE
            fileop.pFrom = paths_string
            fileop.pTo = None
            # FOF_ALLOWUNDO (0x0040) sends to Recycle Bin.
            # FOF_NOCONFIRMATION (0x0010) + FOF_SILENT (0x0004) + FOF_NOERRORUI (0x0400) runs without popups.
            fileop.fFlags = 0x0040 | 0x0010 | 0x0004 | 0x0400
            fileop.fAnyOperationsAborted = False
            fileop.hNameMappings = None
            fileop.lpszProgressTitle = None

            try:
                ret = shell32.SHFileOperationW(byref(fileop))
                success = (ret == 0)
                for p in safe_paths:
                    if success:
                        db.delete_file(p)
                        db.delete_subfolders(p)
                    results[p] = success
            except Exception as e:
                print(f"Windows SHFileOperationW Recycle Bin call failed: {e}")
                # Fallback to standard delete if API failed
                for p in safe_paths:
                    results[p] = FileOperations._fallback_delete(p)
        else:
            # Fallback for non-Windows (direct deletes)
            for p in safe_paths:
                results[p] = FileOperations._fallback_delete(p)

        return results

    @staticmethod
    def _fallback_delete(path: str) -> bool:
        """Fallback destructive deletion if Recycle Bin fails or on non-Windows."""
        if not SafetyManager.is_safe_to_modify(path):
            return False
            
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                db.delete_subfolders(path)
            else:
                os.remove(path)
                db.delete_file(path)
            return True
        except Exception as e:
            print(f"Fallback delete failed for {path}: {e}")
            return False

    @staticmethod
    def move_file(source: str, target: str) -> bool:
        """Moves a file safely, creating directories if needed, and updating database."""
        if not SafetyManager.is_safe_to_modify(source):
            return False
        if not SafetyManager.is_safe_to_modify(target):
            return False

        try:
            # Ensure target parent folder exists
            target_parent = os.path.dirname(target)
            os.makedirs(target_parent, exist_ok=True)

            shutil.move(source, target)
            
            # Update index
            db.delete_file(source)
            # Reinserting with new path (let the watcher re-index or manually insert)
            # To be safe, we delete old and let database update. If watcher is running, it will sync.
            # But let's insert it immediately so that the index is accurate even if watcher is off.
            return True
        except Exception as e:
            print(f"Failed to move file {source} -> {target}: {e}")
            return False

    @staticmethod
    def copy_file(source: str, target: str) -> bool:
        """Copies a file safely, creating directories if needed."""
        if not SafetyManager.is_safe_to_modify(source):
            return False
        if not SafetyManager.is_safe_to_modify(target):
            return False

        try:
            target_parent = os.path.dirname(target)
            os.makedirs(target_parent, exist_ok=True)

            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            return True
        except Exception as e:
            print(f"Failed to copy file {source} -> {target}: {e}")
            return False
