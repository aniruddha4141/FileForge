import mimetypes
import os
from datetime import datetime

# Category classification mapping
EXTENSION_CATEGORIES = {
    # Documents
    "pdf": "Documents", "doc": "Documents", "docx": "Documents", "xls": "Documents",
    "xlsx": "Documents", "ppt": "Documents", "pptx": "Documents", "txt": "Documents",
    "rtf": "Documents", "odt": "Documents", "ods": "Documents", "odp": "Documents",
    "csv": "Documents", "epub": "Documents", "mobi": "Documents", "md": "Documents",
    # Images
    "png": "Images", "jpg": "Images", "jpeg": "Images", "gif": "Images",
    "bmp": "Images", "tiff": "Images", "svg": "Images", "webp": "Images",
    "ico": "Images", "heic": "Images", "psd": "Images", "ai": "Images",
    # Videos
    "mp4": "Videos", "mkv": "Videos", "avi": "Videos", "mov": "Videos",
    "wmv": "Videos", "flv": "Videos", "webm": "Videos", "m4v": "Videos",
    "mpeg": "Videos", "mpg": "Videos", "3gp": "Videos",
    # Audio
    "mp3": "Audio", "wav": "Audio", "flac": "Audio", "ogg": "Audio",
    "m4a": "Audio", "wma": "Audio", "aac": "Audio", "mid": "Audio",
    "midi": "Audio", "opus": "Audio",
    # Archives
    "zip": "Archives", "rar": "Archives", "7z": "Archives", "tar": "Archives",
    "gz": "Archives", "bz2": "Archives", "xz": "Archives", "tgz": "Archives",
    # Executables
    "exe": "Executables", "msi": "Executables", "bat": "Executables", "cmd": "Executables",
    "sh": "Executables", "bin": "Executables", "app": "Executables", "dmg": "Executables",
    # Source Code
    "py": "Source Code", "js": "Source Code", "ts": "Source Code", "jsx": "Source Code",
    "tsx": "Source Code", "html": "Source Code", "css": "Source Code", "scss": "Source Code",
    "cpp": "Source Code", "c": "Source Code", "h": "Source Code", "cs": "Source Code",
    "java": "Source Code", "go": "Source Code", "rs": "Source Code", "php": "Source Code",
    "rb": "Source Code", "sql": "Source Code", "json": "Source Code", "xml": "Source Code",
    "yaml": "Source Code", "yml": "Source Code", "gradle": "Source Code", "kt": "Source Code",
    # Temp / Cache
    "tmp": "Temp/Cache", "temp": "Temp/Cache", "log": "Temp/Cache", "cache": "Temp/Cache",
    "bak": "Backups", "old": "Backups",
}

def format_size(size_bytes: int) -> str:
    """Formats bytes into human-readable sizes."""
    if size_bytes < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size_bytes < 1024.0:
            # Avoid decimal places for Bytes
            if unit == 'B':
                return f"{int(size_bytes)} {unit}"
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def format_datetime(timestamp: float) -> str:
    """Formats epoch timestamp into string."""
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Unknown"

def get_file_category(file_path: str) -> str:
    """Resolves the category of a file based on its extension."""
    _, ext = os.path.splitext(file_path)
    ext_clean = ext.lower().lstrip('.')
    return EXTENSION_CATEGORIES.get(ext_clean, "Miscellaneous")

def get_mime_type(file_path: str) -> str:
    """Resolves mime type of a file, fallback to octet-stream."""
    mime, _ = mimetypes.guess_type(file_path)
    return mime or "application/octet-stream"
