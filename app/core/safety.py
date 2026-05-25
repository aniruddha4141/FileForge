import os
from pathlib import Path
from app.core.config import config

class SafetyManager:
    SYSTEM_CRITICAL_NAMES = {
        "windows", "system32", "program files", "program files (x86)",
        "winnt", "system volume information", "$recycle.bin", "recovery",
        "boot", "msocache", "programdata", "documents and settings"
    }

    SYSTEM_CRITICAL_FILES = {
        "ntldr", "bootmgr", "pagefile.sys", "hiberfil.sys", "swapfile.sys",
        "ntuser.dat", "ntuser.dat.log", "usrclass.dat"
    }

    @classmethod
    def is_safe_to_modify(cls, path_str: str) -> bool:
        """
        Determines whether a file or directory is safe to delete or move.
        Returns False if the path is system-critical or protected.
        """
        try:
            path = Path(path_str).resolve()
        except Exception:
            return False  # If path is invalid or can't be resolved, protect it

        # 1. Block root directory of any drive (e.g., C:\, D:\)
        if len(path.parts) <= 1 or path.parent == path:
            return False

        # 2. Block system-critical folders on Windows
        parts_lower = [p.lower() for p in path.parts]
        for name in cls.SYSTEM_CRITICAL_NAMES:
            if name in parts_lower:
                return False

        # 3. Block specific system files
        if path.name.lower() in cls.SYSTEM_CRITICAL_FILES:
            return False

        # 4. Check against user home root directories directly
        try:
            home = Path.home().resolve()
            if path == home or path == home.parent or path == home.parent.parent:
                return False
        except Exception:
            pass

        # 5. Check against FileForge configuration directories
        try:
            if config.config_dir.resolve() in path.parents or path == config.config_dir.resolve():
                return False
        except Exception:
            pass

        # 6. Check against user-configured protected paths
        user_protected = config.get("protected_paths", [])
        for protected_str in user_protected:
            try:
                protected_path = Path(protected_str).resolve()
                if path == protected_path or protected_path in path.parents:
                    return False
            except Exception:
                pass

        return True

    @classmethod
    def filter_safe_paths(cls, path_list: list[str]) -> list[str]:
        """Filters a list of path strings, returning only those that are safe to modify."""
        return [p for p in path_list if cls.is_safe_to_modify(p)]
