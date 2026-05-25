import os
import sys
import shutil
import zipfile
import struct
import subprocess

def log_step(msg: str):
    print(f"\n[BUILD] === {msg} ===")

def clean_paths(paths):
    for p in paths:
        if os.path.exists(p):
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception as e:
                print(f"Warning: Failed to clean {p}: {e}")

def zip_directory(src_dir: str, zip_path: str):
    """Zips the contents of a directory recursively."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src_dir):
            for file in files:
                full_path = os.path.join(root, file)
                # Keep directory structure relative to src_dir
                rel_path = os.path.relpath(full_path, src_dir)
                z.write(full_path, rel_path)

def append_payload_to_exe(base_exe: str, payload_zip: str, output_exe: str):
    """Appends payload zip bytes and zip size to the base exe binary."""
    with open(base_exe, "rb") as f:
        exe_bytes = f.read()
        
    with open(payload_zip, "rb") as f:
        zip_bytes = f.read()
        
    zip_size = len(zip_bytes)
    # Pack size as 64-bit unsigned integer (little-endian)
    size_suffix = struct.pack("<Q", zip_size)
    
    with open(output_exe, "wb") as f:
        f.write(exe_bytes)
        f.write(zip_bytes)
        f.write(size_suffix)
    print(f"Appended zip payload ({zip_size} bytes) to create {output_exe}")

def build_releases():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(project_root, "dist")
    build_dir = os.path.join(project_root, "build")
    
    release_dir = os.path.join(project_root, "..", "FileForge Release")
    portable_dir = os.path.join(release_dir, "Portable")
    
    # 0. Generate .ico from .png for Windows executable icons
    png_path = os.path.join(project_root, "assets", "logo.png")
    ico_path = os.path.join(project_root, "assets", "logo.ico")
    if os.path.exists(png_path) and not os.path.exists(ico_path):
        log_step("Generating Windows executable icon (logo.ico)...")
        from PIL import Image
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        
    # 1. Clean previous build folders
    log_step("Cleaning workspace build folders...")
    clean_paths([dist_dir, build_dir, release_dir])
    os.makedirs(portable_dir, exist_ok=True)

    # Resolve executable paths
    pyinstaller = "pyinstaller"
    
    # 2. Compile FileForge in --onedir mode
    log_step("Compiling FileForge Directory payload...")
    cmd_dir = [
        pyinstaller,
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--add-data", "assets;assets",
        "--icon", ico_path,
        "--name", "FileForge",
        "--clean",
        os.path.join(project_root, "run.py")
    ]
    subprocess.check_call(cmd_dir, cwd=project_root)

    # 3. Zip the directory payload
    log_step("Archiving FileForge directory payload into payload.zip...")
    payload_dir = os.path.join(dist_dir, "FileForge")
    zip_payload_path = os.path.join(dist_dir, "payload.zip")
    zip_directory(payload_dir, zip_payload_path)

    # 4. Copy payload.zip to packaging folder for debug setup testing
    shutil.copy2(zip_payload_path, os.path.join(project_root, "packaging", "payload.zip"))

    # 5. Compile app_installer.py in --onefile mode
    log_step("Compiling Setup base loader...")
    cmd_setup = [
        pyinstaller,
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--icon", ico_path,
        "--name", "Setup_Base",
        "--clean",
        os.path.join(project_root, "packaging", "app_installer.py")
    ]
    subprocess.check_call(cmd_setup, cwd=project_root)

    # 6. Append payload.zip to Setup_Base.exe to make final Setup.exe
    log_step("Assembling final Setup.exe...")
    base_exe = os.path.join(dist_dir, "Setup_Base.exe")
    output_setup = os.path.join(release_dir, "Setup.exe")
    append_payload_to_exe(base_exe, zip_payload_path, output_setup)

    # 7. Compile FileForge in --onefile mode (Portable version)
    log_step("Compiling Portable FileForge.exe (one-file)...")
    cmd_portable = [
        pyinstaller,
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--add-data", "assets;assets",
        "--icon", ico_path,
        "--name", "FileForge",
        "--clean",
        os.path.join(project_root, "run.py")
    ]
    subprocess.check_call(cmd_portable, cwd=project_root)

    # 8. Copy Portable FileForge.exe to FileForge Release/Portable/
    log_step("Copying Portable binary to release folder...")
    portable_exe = os.path.join(dist_dir, "FileForge.exe")
    shutil.copy2(portable_exe, os.path.join(portable_dir, "FileForge.exe"))

    # 9. Copy Github release notes file
    log_step("Generating GitHub Release Tab documentation...")
    output_notes = os.path.join(release_dir, "github_release_tab.md")
    generate_release_notes(output_setup, os.path.join(portable_dir, "FileForge.exe"), output_notes)

    log_step("Releases folder populated!")
    print(f"Setup Installer: {output_setup}")
    print(f"Portable Build:  {os.path.join(portable_dir, 'FileForge.exe')}")
    print(f"Release Notes:   {output_notes}")
    
    # Clean temporary payload.zip
    clean_paths([os.path.join(project_root, "packaging", "payload.zip")])

def calculate_sha256(file_path: str) -> str:
    """Calculates SHA-256 checksum of a file."""
    import hashlib
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def generate_release_notes(setup_exe: str, portable_exe: str, output_path: str):
    """Generates the GitHub Release Notes markdown file with checksums."""
    setup_hash = calculate_sha256(setup_exe)
    portable_hash = calculate_sha256(portable_exe)
    
    notes = f"""# FileForge Release v1.0.0

FileForge is a high-performance offline desktop application for intelligent file organization, duplicates resolution, advanced search, and storage health analytics.

## Release Binaries
For security and file integrity validation, verify the SHA-256 hashes of the files before executing:

| File | Type | SHA-256 Checksum |
| :--- | :--- | :--- |
| **`Setup.exe`** | Graphical Setup Wizard | `{setup_hash}` |
| **`FileForge.exe`** | Portable Version | `{portable_hash}` |

---

## What's New in v1.0.0

- **Parallel Directory Crawler:** Traverses files concurrently using `os.scandir` to extract folder branches, writing metadata to an SQLite cache in batched transactions.
- **Squarified Treemap Map:** Visualizes directory sizes using the squarified treemap layout drawn inside a custom painted viewport. Double-click to zoom in, right-click to zoom out.
- **3-Phase Duplicate Hashing:** screens identical byte sizes in SQLite, pre-checks 8KB headers via `xxhash`, and hashes full files concurrently using xxhash with database caching.
- **Advanced Local Search:** Utilizes SQLite FTS5 index for instant substring/wildcard searches. Left-double-click opens the file; right-click locates the file in File Explorer or sends it to the Recycle Bin.
- **Operation undo Manager:** Logs moves/copies in SQLite, enabling one-click session rollbacks.
- **Beginner-Safe Deletions:** Integrates with ctypes Windows `SHFileOperationW` Shell APIs to safely send files to the native Windows Recycle Bin.

## Installation Guidelines

### Setup Installer (`Setup.exe`)
1. Download and launch `Setup.exe`.
2. Choose the installation directory (defaults to user program path).
3. The wizard extracts the bundle and registers desktop & start menu shortcuts.
4. Click Finish to automatically run FileForge.

### Portable Version (`Portable/FileForge.exe`)
1. Download the executable and place it anywhere (Desktop, USB, external drives).
2. Launch it directly to start organizing your files. No installation or shortcuts will be created.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(notes)
    print(f"Generated GitHub Release notes at {output_path}")

if __name__ == "__main__":
    try:
        build_releases()
        print("\n[BUILD] BUILD SUCCESSFUL!")
    except Exception as e:
        print(f"\n[BUILD] BUILD FAILED: {e}")
        sys.exit(1)
