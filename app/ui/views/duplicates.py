from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QTreeWidget, QTreeWidgetItem, QProgressBar, QMessageBox
from PyQt6.QtCore import pyqtSlot, Qt
from app.duplicate_detection.finder import DuplicateFinder, select_duplicate_removals
from app.cleanup.operations import FileOperations
from app.recovery.registry import recovery_registry
from app.utils.helpers import format_size, format_datetime

class DuplicatesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.finder = None
        self.duplicate_groups = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Action Panel
        action_frame = QFrame()
        action_frame.setObjectName("CardFrame")
        af_layout = QHBoxLayout(action_frame)

        self.scan_btn = QPushButton("Scan for Duplicates")
        self.scan_btn.setObjectName("PrimaryButton")
        self.scan_btn.clicked.connect(self._start_duplicates_scan)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_duplicates_scan)

        af_layout.addWidget(self.scan_btn)
        af_layout.addWidget(self.cancel_btn)
        af_layout.addStretch()

        layout.addWidget(action_frame)

        # 2. Progress Frame (Hidden by default)
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("CardFrame")
        self.progress_frame.setVisible(False)
        pf_layout = QVBoxLayout(self.progress_frame)
        
        self.progress_status = QLabel("Evaluating duplicates...")
        self.progress_status.setStyleSheet("font-weight: bold; color: #00f0ff;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        pf_layout.addWidget(self.progress_status)
        pf_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_frame)

        # 3. Presets and Results Frame
        self.results_frame = QFrame()
        self.results_frame.setObjectName("CardFrame")
        rf_layout = QVBoxLayout(self.results_frame)

        # Presets Row
        presets_layout = QHBoxLayout()
        presets_lbl = QLabel("Selection Presets:")
        presets_lbl.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 13px;")
        
        self.keep_oldest_btn = QPushButton("Keep Oldest (Select New)")
        self.keep_oldest_btn.setObjectName("SecondaryButton")
        self.keep_oldest_btn.clicked.connect(lambda: self._apply_selection_preset("newest"))

        self.keep_newest_btn = QPushButton("Keep Newest (Select Old)")
        self.keep_newest_btn.setObjectName("SecondaryButton")
        self.keep_newest_btn.clicked.connect(lambda: self._apply_selection_preset("oldest"))

        self.keep_shortest_btn = QPushButton("Keep Shortest Path")
        self.keep_shortest_btn.setObjectName("SecondaryButton")
        self.keep_shortest_btn.clicked.connect(lambda: self._apply_selection_preset("path_length"))

        self.unselect_btn = QPushButton("Unselect All")
        self.unselect_btn.setObjectName("SecondaryButton")
        self.unselect_btn.clicked.connect(self._unselect_all)

        presets_layout.addWidget(presets_lbl)
        presets_layout.addWidget(self.keep_oldest_btn)
        presets_layout.addWidget(self.keep_newest_btn)
        presets_layout.addWidget(self.keep_shortest_btn)
        presets_layout.addWidget(self.unselect_btn)
        presets_layout.addStretch()
        rf_layout.addLayout(presets_layout)

        # Duplicate Tree
        self.tree = QTreeWidget()
        self.tree.setObjectName("DuplicateTree")
        self.tree.setStyleSheet("background-color: transparent; border: none; color: #e2e8f0; font-size: 13px;")
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["File Name / Path", "Size", "Date Modified"])
        self.tree.setColumnWidth(0, 450)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 150)
        rf_layout.addWidget(self.tree)

        # Clean Button Row
        clean_row = QHBoxLayout()
        self.clean_btn = QPushButton("Clean Selected Duplicates")
        self.clean_btn.setObjectName("PrimaryButton")
        self.clean_btn.clicked.connect(self._clean_selected_duplicates)
        
        clean_row.addStretch()
        clean_row.addWidget(self.clean_btn)
        rf_layout.addLayout(clean_row)

        layout.addWidget(self.results_frame)

    def update_theme(self, theme: str):
        if theme == "light":
            self.progress_status.setStyleSheet("font-weight: bold; color: #0066cc;")
            self.tree.setStyleSheet("background-color: transparent; border: none; color: #334155; font-size: 13px;")
        else:
            self.progress_status.setStyleSheet("font-weight: bold; color: #00f0ff;")
            self.tree.setStyleSheet("background-color: transparent; border: none; color: #e2e8f0; font-size: 13px;")

    def _start_duplicates_scan(self):
        self.tree.clear()
        self.duplicate_groups.clear()
        
        self.scan_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_status.setText("Initiating database duplicate screening...")

        # Spawn DuplicateFinder Thread
        self.finder = DuplicateFinder()
        self.finder.progress_updated.connect(self._on_finder_progress)
        self.finder.finished.connect(self._on_finder_finished)
        self.finder.error.connect(self._on_finder_error)
        self.finder.start()

    def _cancel_duplicates_scan(self):
        if self.finder:
            self.progress_status.setText("Stopping duplicate search...")
            self.finder.cancel()

    @pyqtSlot(dict)
    def _on_finder_progress(self, stats: dict):
        self.progress_status.setText(stats["status"])
        self.progress_bar.setValue(stats["percent"])

    @pyqtSlot(dict)
    def _on_finder_finished(self, groups: dict):
        self.duplicate_groups = groups
        self.progress_frame.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        self._populate_tree()

    @pyqtSlot(str)
    def _on_finder_error(self, err: str):
        self.progress_frame.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        QMessageBox.critical(self, "Duplicate Finder Error", f"Failed to search duplicates: {err}")

    def _populate_tree(self):
        self.tree.clear()
        
        if not self.duplicate_groups:
            # Show empty placeholder
            parent_item = QTreeWidgetItem(self.tree)
            parent_item.setText(0, "No duplicate files found in current index.")
            return

        for hash_val, file_list in self.duplicate_groups.items():
            first_file = file_list[0]
            size_str = format_size(first_file["size"])
            
            # Create a parent group item
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"Duplicate Group ({len(file_list)} files) — Hash: {hash_val[:12]}...")
            group_item.setText(1, size_str)
            # Expand parent items by default
            group_item.setExpanded(True)
            
            for file_rec in file_list:
                child_item = QTreeWidgetItem(group_item)
                child_item.setText(0, file_rec["path"])
                child_item.setText(1, size_str)
                child_item.setText(2, format_datetime(file_rec["modified_at"]))
                
                # Make checkable
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child_item.setCheckState(0, Qt.CheckState.Unchecked)
                # Store path in user role data
                child_item.setData(0, Qt.ItemDataRole.UserRole, file_rec["path"])

    def _apply_selection_preset(self, preset_name: str):
        """Finds paths to select based on criteria and updates tree checkboxes."""
        paths_to_select = select_duplicate_removals(self.duplicate_groups, preset_name)
        paths_set = set(paths_to_select)

        # Loop through QTreeWidget items and check matching paths
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                path = child.data(0, Qt.ItemDataRole.UserRole)
                if path in paths_set:
                    child.setCheckState(0, Qt.CheckState.Checked)
                else:
                    child.setCheckState(0, Qt.CheckState.Unchecked)

    def _unselect_all(self):
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                child.setCheckState(0, Qt.CheckState.Unchecked)

    def _clean_selected_duplicates(self):
        selected_paths = []
        
        # Traverse tree and grab checked items
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    if path:
                        selected_paths.append(path)

        if not selected_paths:
            QMessageBox.information(self, "Clean Duplicates", "No duplicates selected for removal.")
            return

        reply = QMessageBox.warning(
            self, 
            "Clean Duplicate Files",
            f"Are you sure you want to move the {len(selected_paths)} selected duplicate files to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            session_id = recovery_registry.start_session("Clean Duplicate Files")
            
            results = FileOperations.send_to_recycle_bin(selected_paths)
            
            success_cnt = 0
            for p, ok in results.items():
                if ok:
                    success_cnt += 1
                    recovery_registry.log_action(session_id, "delete", p, None)

            QMessageBox.information(
                self, 
                "Cleanup Finished", 
                f"Successfully sent {success_cnt}/{len(selected_paths)} duplicates to the Windows Recycle Bin."
            )

            # Rebuild tree with remaining groups
            # Remove deleted files from groups dictionary
            new_groups = {}
            for h, files in self.duplicate_groups.items():
                remaining_files = [f for f in files if f["path"] not in results or not results[f["path"]]]
                if len(remaining_files) > 1:
                    new_groups[h] = remaining_files
            self.duplicate_groups = new_groups
            self._populate_tree()
