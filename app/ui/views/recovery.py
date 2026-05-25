from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QMessageBox, QSplitter
from PyQt6.QtCore import pyqtSlot, Qt
from app.recovery.registry import recovery_registry
from app.utils.helpers import format_datetime

class RecoveryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions_list = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Description Label
        desc = QLabel("Review file modification logs and rollback previous file organization or backup runs.")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Splitter to separate Session list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel: Session History list
        history_frame = QFrame()
        history_frame.setObjectName("CardFrame")
        hf_layout = QVBoxLayout(history_frame)
        
        history_title = QLabel("Operations History")
        history_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #94a3b8;")
        hf_layout.addWidget(history_title)

        self.session_list_widget = QListWidget()
        self.session_list_widget.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #e2e8f0;")
        self.session_list_widget.currentItemChanged.connect(self._on_session_selection_changed)
        hf_layout.addWidget(self.session_list_widget)

        self.refresh_btn = QPushButton("Refresh Logs")
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.clicked.connect(self.load_sessions)
        hf_layout.addWidget(self.refresh_btn)

        splitter.addWidget(history_frame)

        # Right panel: Details tree and Rollback button
        details_frame = QFrame()
        details_frame.setObjectName("CardFrame")
        df_layout = QVBoxLayout(details_frame)

        details_title = QLabel("Session Action Details")
        details_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #94a3b8;")
        df_layout.addWidget(details_title)

        self.details_tree = QTreeWidget()
        self.details_tree.setStyleSheet("background-color: transparent; border: none; color: #e2e8f0; font-size: 13px;")
        self.details_tree.setColumnCount(3)
        self.details_tree.setHeaderLabels(["Action", "Original Source", "Target Location"])
        self.details_tree.setColumnWidth(0, 100)
        self.details_tree.setColumnWidth(1, 280)
        self.details_tree.setColumnWidth(2, 280)
        df_layout.addWidget(self.details_tree)

        # Rollback Button Row
        rollback_row = QHBoxLayout()
        self.rollback_btn = QPushButton("Rollback / Undo Session")
        self.rollback_btn.setObjectName("PrimaryButton")
        self.rollback_btn.setEnabled(False)
        self.rollback_btn.clicked.connect(self._on_rollback_clicked)
        
        rollback_row.addStretch()
        rollback_row.addWidget(self.rollback_btn)
        df_layout.addLayout(rollback_row)

        splitter.addWidget(details_frame)
        
        # Splitter proportions: 35% left, 65% right
        splitter.setSizes([300, 550])

        layout.addWidget(splitter)

    def update_theme(self, theme: str):
        if theme == "light":
            self.session_list_widget.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #334155;")
            self.details_tree.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #334155;")
        else:
            self.session_list_widget.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #e2e8f0;")
            self.details_tree.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #e2e8f0;")

    @pyqtSlot()
    def load_sessions(self):
        """Loads operations history sessions from the registry."""
        self.session_list_widget.clear()
        self.details_tree.clear()
        self.rollback_btn.setEnabled(False)

        self.sessions_list = recovery_registry.get_sessions()
        
        if not self.sessions_list:
            item = QListWidgetItem("No file operations logged yet.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.session_list_widget.addItem(item)
            return

        for idx, s in enumerate(self.sessions_list):
            dt_str = format_datetime(s["timestamp"])
            item_text = f" {dt_str}\n  {s['description']}"
            item = QListWidgetItem(item_text)
            # Store session_id
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            self.session_list_widget.addItem(item)

    def _on_session_selection_changed(self, current_item, previous_item):
        self.details_tree.clear()
        
        if not current_item:
            self.rollback_btn.setEnabled(False)
            return

        session_id = current_item.data(Qt.ItemDataRole.UserRole)
        if session_id is None:
            self.rollback_btn.setEnabled(False)
            return

        self.rollback_btn.setEnabled(True)

        # Query actions for selected session
        actions = recovery_registry.get_session_actions(session_id)
        for act in actions:
            item = QTreeWidgetItem(self.details_tree)
            item.setText(0, act["action_type"].upper())
            item.setText(1, act["source"])
            item.setText(2, act["target"] or "Windows Recycle Bin")

    def _on_rollback_clicked(self):
        current_item = self.session_list_widget.currentItem()
        if not current_item:
            return

        session_id = current_item.data(Qt.ItemDataRole.UserRole)
        if session_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Rollback File Operations",
            "Are you sure you want to reverse all file operations for this session?\nThis will move files back to their original locations.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, fail, msg = recovery_registry.rollback_session(session_id)
            
            QMessageBox.information(
                self,
                "Rollback Finished",
                msg
            )
            
            # Reload registry log
            self.load_sessions()
