from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame, QTableView, QHeaderView, QMenu, QMessageBox, QCheckBox, QComboBox
from PyQt6.QtCore import pyqtSlot, Qt, QPoint
from app.indexing.db import db
from app.ui.widgets.table import FileTableModel
from app.cleanup.operations import FileOperations
from app.recovery.registry import recovery_registry
import os
import subprocess

class SearchView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Search Bar & Filter Controls
        filter_frame = QFrame()
        filter_frame.setObjectName("CardFrame")
        ff_layout = QVBoxLayout(filter_frame)
        ff_layout.setSpacing(10)

        # Search box row
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search file names or paths instantly (supports wildcards)...")
        self.search_input.returnPressed.connect(self._perform_search)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("PrimaryButton")
        self.search_btn.clicked.connect(self._perform_search)
        
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        ff_layout.addLayout(search_row)

        # Detailed filters row
        details_row = QHBoxLayout()
        
        # Category filter combo
        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.cat_combo = QComboBox()
        self.cat_combo.addItems([
            "All Categories", "Documents", "Images", "Videos", "Audio",
            "Archives", "Executables", "Source Code", "Temp/Cache", "Miscellaneous"
        ])
        
        # Size filter combo
        size_lbl = QLabel("Size:")
        size_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "Any Size", 
            "Large (> 100 MB)", 
            "Huge (> 1 GB)", 
            "Tiny (< 1 MB)", 
            "Medium (1 - 100 MB)"
        ])

        # Extension filter
        ext_lbl = QLabel("Extension:")
        ext_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText("e.g. pdf (no dot)")
        self.ext_input.setMaximumWidth(120)
        self.ext_input.returnPressed.connect(self._perform_search)

        details_row.addWidget(cat_lbl)
        details_row.addWidget(self.cat_combo)
        details_row.addWidget(size_lbl)
        details_row.addWidget(self.size_combo)
        details_row.addWidget(ext_lbl)
        details_row.addWidget(self.ext_input)
        details_row.addStretch()
        ff_layout.addLayout(details_row)

        layout.addWidget(filter_frame)

        # 2. Virtual Table View
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        
        # Bind Virtual Model
        self.model = FileTableModel()
        self.table.setModel(self.model)
        
        # Configure Table Headers
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(26)
        
        # Interaction bindings
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

    def update_theme(self, theme: str):
        pass  # Styled via standard QSS rules

    def _perform_search(self):
        query = self.search_input.text().strip()
        
        # Parse Category filter
        cat = self.cat_combo.currentText()
        categories = None
        if cat != "All Categories":
            categories = [cat]

        # Parse Size filter
        size_filter = self.size_combo.currentText()
        min_size = None
        max_size = None
        
        if size_filter == "Large (> 100 MB)":
            min_size = 100 * 1024 * 1024
        elif size_filter == "Huge (> 1 GB)":
            min_size = 1024 * 1024 * 1024
        elif size_filter == "Tiny (< 1 MB)":
            max_size = 1024 * 1024
        elif size_filter == "Medium (1 - 100 MB)":
            min_size = 1024 * 1024
            max_size = 100 * 1024 * 1024

        # Parse Extension filter
        ext = self.ext_input.text().strip()
        if not ext:
            ext = None

        # Query Database
        results = db.search_fts(query, categories, min_size, max_size, ext)
        
        # Update Table Model
        self.model.set_files(results)
        
        # Adjust Columns Sizes
        self.table.setColumnWidth(0, 200) # Name
        self.table.setColumnWidth(1, 100) # Category
        self.table.setColumnWidth(2, 90)  # Size
        self.table.setColumnWidth(3, 140) # Date

    def _on_row_double_clicked(self, index):
        if not index.isValid():
            return
            
        file_rec = self.model.data(index, role=Qt.ItemDataRole.UserRole)
        if file_rec:
            path = file_rec["path"]
            try:
                # Launch default OS program associated with file
                os.startfile(path)
            except Exception as e:
                QMessageBox.critical(self, "Open File", f"Failed to launch file: {e}")

    def _show_context_menu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        file_rec = self.model.data(index, role=Qt.ItemDataRole.UserRole)
        if not file_rec:
            return

        path = file_rec["path"]

        menu = QMenu(self)
        open_action = menu.addAction("Open / Run File")
        explorer_action = menu.addAction("Show in File Explorer")
        menu.addSeparator()
        delete_action = menu.addAction("Move to Recycle Bin")

        # Execute selected action
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        
        if action == open_action:
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.critical(self, "Open File", f"Failed to launch file: {e}")
                
        elif action == explorer_action:
            try:
                if os.name == 'nt':
                    # Highlight file in windows explorer
                    subprocess.Popen(f'explorer /select,"{os.path.abspath(path)}"')
                else:
                    # Fallback for parent directory
                    os.startfile(os.path.dirname(path))
            except Exception as e:
                print(f"Failed to open explorer: {e}")
                
        elif action == delete_action:
            reply = QMessageBox.warning(
                self, 
                "Delete File",
                f"Are you sure you want to move this file to the Recycle Bin?\n\n{path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                session_id = recovery_registry.start_session("Delete File from Search")
                results = FileOperations.send_to_recycle_bin([path])
                if results.get(path, False):
                    recovery_registry.log_action(session_id, "delete", path, None)
                    QMessageBox.information(self, "Delete File", "File sent to the Windows Recycle Bin.")
                    # Refresh search results
                    self._perform_search()
                else:
                    QMessageBox.critical(self, "Delete File", "Failed to delete file. It may be locked or permission denied.")
