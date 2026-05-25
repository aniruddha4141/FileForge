import os
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QListWidget, QListWidgetItem, QTabWidget, QMessageBox, QCheckBox
from PyQt6.QtCore import pyqtSlot
from app.indexing.db import db
from app.cleanup.operations import FileOperations
from app.recovery.registry import recovery_registry
from app.utils.helpers import format_size, format_datetime

class CleanupView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dev_folders_list: List[Dict[str, Any]] = []
        self.download_files_list: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Tab Widget to separate Developer Workspace and Downloads
        self.tabs = QTabWidget()
        
        # Tab 1: Developer Cleanup
        dev_widget = QWidget()
        dev_layout = QVBoxLayout(dev_widget)
        dev_layout.setSpacing(10)
        
        dev_desc = QLabel("Detect and clean large developer workspace build artifacts and dependencies (e.g. node_modules, target, venv, pycache).")
        dev_desc.setWordWrap(True)
        dev_desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        dev_layout.addWidget(dev_desc)

        self.dev_list = QListWidget()
        self.dev_list.setStyleSheet("background-color: #111a2e; border: 1px solid #1e293b; border-radius: 8px; padding: 5px;")
        dev_layout.addWidget(self.dev_list)

        dev_btn_layout = QHBoxLayout()
        self.dev_scan_btn = QPushButton("Scan Workspace leftovers")
        self.dev_scan_btn.setObjectName("SecondaryButton")
        self.dev_scan_btn.clicked.connect(self.scan_developer_leftovers)

        self.dev_clean_btn = QPushButton("Clean Selected Workspace Folders")
        self.dev_clean_btn.setObjectName("PrimaryButton")
        self.dev_clean_btn.clicked.connect(self.clean_selected_dev_folders)

        dev_btn_layout.addWidget(self.dev_scan_btn)
        dev_btn_layout.addStretch()
        dev_btn_layout.addWidget(self.dev_clean_btn)
        dev_layout.addLayout(dev_btn_layout)

        self.tabs.addTab(dev_widget, "Developer Workspace Cleanup")

        # Tab 2: Downloads Organizer
        dl_widget = QWidget()
        dl_layout = QVBoxLayout(dl_widget)
        dl_layout.setSpacing(10)

        dl_desc = QLabel("Identify clutter in Downloads directory (old installers, forgotten archives, large unused files).")
        dl_desc.setWordWrap(True)
        dl_desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        dl_layout.addWidget(dl_desc)

        self.dl_list = QListWidget()
        self.dl_list.setStyleSheet("background-color: #111a2e; border: 1px solid #1e293b; border-radius: 8px; padding: 5px;")
        dl_layout.addWidget(self.dl_list)

        dl_btn_layout = QHBoxLayout()
        self.dl_scan_btn = QPushButton("Scan Downloads clutter")
        self.dl_scan_btn.setObjectName("SecondaryButton")
        self.dl_scan_btn.clicked.connect(self.scan_downloads_clutter)

        self.dl_clean_btn = QPushButton("Clean Selected Downloads Clutter")
        self.dl_clean_btn.setObjectName("PrimaryButton")
        self.dl_clean_btn.clicked.connect(self.clean_selected_downloads)

        dl_btn_layout.addWidget(self.dl_scan_btn)
        dl_btn_layout.addStretch()
        dl_btn_layout.addWidget(self.dl_clean_btn)
        dl_layout.addLayout(dl_btn_layout)

        self.tabs.addTab(dl_widget, "Downloads Organizer")

        main_layout.addWidget(self.tabs)

    def update_theme(self, theme: str):
        if theme == "light":
            for lst in [self.dev_list, self.dl_list]:
                lst.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 5px; color: #0f172a;")
        else:
            for lst in [self.dev_list, self.dl_list]:
                lst.setStyleSheet("background-color: #111a2e; border: 1px solid #1e293b; border-radius: 8px; padding: 5px; color: #e2e8f0;")

    @pyqtSlot()
    def scan_developer_leftovers(self):
        """Scans indexed DB for workspace folders that match developer metadata patterns."""
        self.dev_list.clear()
        self.dev_folders_list.clear()

        # Connect to DB and fetch all files under target patterns
        conn = db.get_connection()
        cursor = conn.cursor()
        
        target_names = ["node_modules", "__pycache__", "venv", "target", "build", "dist", ".gradle"]
        
        # Build SQL: look for paths containing standard Windows or POSIX separator
        # e.g., .../node_modules/ or ...\node_modules\
        where_clauses = []
        params = []
        for name in target_names:
            where_clauses.append("path LIKE ?")
            params.append(f"%/{name}/%")
            where_clauses.append("path LIKE ?")
            params.append(f"%\\{name}\\%")
            # Or ending in node_modules
            where_clauses.append("path LIKE ?")
            params.append(f"%/{name}")
            where_clauses.append("path LIKE ?")
            params.append(f"%\\{name}")

        sql = f"SELECT path, size FROM files WHERE {' OR '.join(where_clauses)};"
        
        try:
            cursor.execute(sql, params)
            matching_files = cursor.fetchall()
        except Exception as e:
            print(f"Error querying dev leftovers: {e}")
            matching_files = []
        finally:
            conn.close()

        # Map files to their parent dev folders:
        # e.g. path="d:/projects/my-app/node_modules/lodash/package.json" -> root="d:/projects/my-app/node_modules"
        dev_roots: Dict[str, Dict[str, Any]] = {}
        for f in matching_files:
            path = f["path"]
            size = f["size"]
            
            # Find the top-level matching directory segment
            found_root = None
            for name in target_names:
                # Look for name in parts
                parts = Path(path).parts
                if name in parts:
                    idx = parts.index(name)
                    # Join parts up to idx+1
                    found_root = str(Path(*parts[:idx+1]))
                    break
                    
            if found_root:
                # Handle Windows drive letters formatting correctly
                if len(found_root) > 1 and found_root[1] == ':':
                    # Path(*parts) on Windows sometimes merges letters weirdly, normalize slashes
                    found_root = os.path.abspath(found_root)
                    
                if found_root not in dev_roots:
                    dev_roots[found_root] = {
                        "path": found_root,
                        "size": 0,
                        "file_count": 0,
                        "type": os.path.basename(found_root)
                    }
                dev_roots[found_root]["size"] += size
                dev_roots[found_root]["file_count"] += 1

        self.dev_folders_list = sorted(list(dev_roots.values()), key=lambda x: x["size"], reverse=True)

        if not self.dev_folders_list:
            self.dev_list.addItem("No developer workspace build folders found in the current index cache.")
            return

        for item_data in self.dev_folders_list:
            # Create a QListWidgetItem with custom checkbox
            item_text = f" [{item_data['type'].upper()}]  {item_data['path']}  ({format_size(item_data['size'])} - {item_data['file_count']} files)"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            # Store raw path in item custom role data
            item.setData(Qt.ItemDataRole.UserRole, item_data["path"])
            self.dev_list.addItem(item)

    @pyqtSlot()
    def clean_selected_dev_folders(self):
        selected_paths = []
        for i in range(self.dev_list.count()):
            item = self.dev_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    selected_paths.append(path)

        if not selected_paths:
            QMessageBox.information(self, "Clean Workspaces", "No directories selected for cleanup.")
            return

        reply = QMessageBox.warning(
            self, 
            "Clean Developer Workspace Leftovers",
            f"Are you sure you want to move the {len(selected_paths)} selected directories to the Recycle Bin?\nThis operation is undoable via the Windows Recycle Bin.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            session_id = recovery_registry.start_session("Clean Developer Workspace Leftovers")
            
            # Executing deletes
            results = FileOperations.send_to_recycle_bin(selected_paths)
            
            success_cnt = 0
            for p, ok in results.items():
                if ok:
                    success_cnt += 1
                    recovery_registry.log_action(session_id, "delete", p, None)

            QMessageBox.information(
                self, 
                "Cleanup Finished", 
                f"Successfully sent {success_cnt}/{len(selected_paths)} folders to the Windows Recycle Bin."
            )
            
            # Re-scan to update list
            self.scan_developer_leftovers()

    @pyqtSlot()
    def scan_downloads_clutter(self):
        """Scans indexed DB downloads category files."""
        self.dl_list.clear()
        self.download_files_list.clear()

        # Connect to DB and query files under a Downloads directory
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Find files matching downloads folder name
        sql = "SELECT * FROM files WHERE path LIKE ? OR path LIKE ? ORDER BY size DESC;"
        params = ["%/downloads/%", "%\\downloads\\%"]
        
        try:
            cursor.execute(sql, params)
            matching_files = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error querying downloads clutter: {e}")
            matching_files = []
        finally:
            conn.close()

        # Filter downloads clutter criteria:
        # 1. Installers (exe, msi) older than 14 days
        # 2. Archives (zip, rar, 7z) older than 30 days
        # 3. Any files older than 60 days
        now_ts = time.time()
        
        self.download_files_list = []
        for f in matching_files:
            age_days = (now_ts - f["modified_at"]) / (24 * 3600)
            ext = f["extension"].lower()
            
            is_clutter = False
            reason = ""
            
            if ext in ["exe", "msi"] and age_days > 14:
                is_clutter = True
                reason = f"Old Installer ({int(age_days)} days old)"
            elif ext in ["zip", "rar", "7z", "tar", "gz"] and age_days > 30:
                is_clutter = True
                reason = f"Old Archive ({int(age_days)} days old)"
            elif age_days > 60:
                is_clutter = True
                reason = f"Dormant File ({int(age_days)} days old)"

            if is_clutter:
                f["clutter_reason"] = reason
                self.download_files_list.append(f)

        if not self.download_files_list:
            self.dl_list.addItem("No downloads clutter detected in current index.")
            return

        for item_data in self.download_files_list:
            item_text = f" [{item_data['clutter_reason']}]  {item_data['name']}  ({format_size(item_data['size'])} - {item_data['path']})"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, item_data["path"])
            self.dl_list.addItem(item)

    @pyqtSlot()
    def clean_selected_downloads(self):
        selected_paths = []
        for i in range(self.dl_list.count()):
            item = self.dl_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    selected_paths.append(path)

        if not selected_paths:
            QMessageBox.information(self, "Downloads Organizer", "No files selected for cleanup.")
            return

        reply = QMessageBox.warning(
            self, 
            "Clean Downloads Clutter",
            f"Are you sure you want to move the {len(selected_paths)} selected files to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            session_id = recovery_registry.start_session("Clean Downloads Clutter")
            
            results = FileOperations.send_to_recycle_bin(selected_paths)
            
            success_cnt = 0
            for p, ok in results.items():
                if ok:
                    success_cnt += 1
                    recovery_registry.log_action(session_id, "delete", p, None)

            QMessageBox.information(
                self, 
                "Cleanup Finished", 
                f"Successfully sent {success_cnt}/{len(selected_paths)} files to the Windows Recycle Bin."
            )
            
            # Re-scan to update list
            self.scan_downloads_clutter()
