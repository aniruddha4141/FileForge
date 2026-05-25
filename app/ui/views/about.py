import os
import sys
import webbrowser
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, pyqtSlot

def get_asset_path(relative_path: str) -> str:
    """Resolves asset paths under PyInstaller environment or local runs."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Local fallback
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    return os.path.join(base_dir, relative_path)

class AboutView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_color = "#111a2e"
        self.text_color = "#e2e8f0"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Center card container
        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Logo
        self.logo_lbl = QLabel()
        logo_path = get_asset_path("assets/logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            # Scale logo to look neat
            self.logo_lbl.setPixmap(pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_lbl.setText("[ LOGO ]")
            self.logo_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #00f0ff;")
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.logo_lbl)

        # 2. Title
        title = QLabel("FileForge")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00f0ff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # 3. Version info
        version = QLabel("Version 1.0.0 Stable (Build: 2026.05.25)")
        version.setStyleSheet("font-size: 13px; color: #94a3b8; font-weight: 500;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(version)

        # 4. Description
        desc = QLabel(
            "FileForge is a high-performance offline desktop application built for intelligent "
            "file organization, storage analytics, duplicate detection, and safe workspace cleanup.<br/><br/>"
            "Operating 100% offline, FileForge guarantees absolute privacy—keeping your indexed directory "
            "metadata entirely on your local machine."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("font-size: 14px; color: #cbd5e1; line-height: 1.5; max-width: 460px;")
        card_layout.addWidget(desc)

        # 5. Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.repo_btn = QPushButton("GitHub Repository")
        self.repo_btn.setObjectName("PrimaryButton")
        self.repo_btn.clicked.connect(self._open_repo)

        self.release_btn = QPushButton("Check Latest Release")
        self.release_btn.setObjectName("SecondaryButton")
        self.release_btn.clicked.connect(self._open_releases)

        self.check_btn = QPushButton("Check Updates")
        self.check_btn.setObjectName("SecondaryButton")
        self.check_btn.clicked.connect(self._check_updates_offline)

        btn_layout.addWidget(self.repo_btn)
        btn_layout.addWidget(self.release_btn)
        btn_layout.addWidget(self.check_btn)
        card_layout.addLayout(btn_layout)

        layout.addWidget(card)
        layout.addStretch()

    def update_theme(self, theme: str):
        if theme == "light":
            self.bg_color = "#ffffff"
            self.text_color = "#334155"
        else:
            self.bg_color = "#111a2e"
            self.text_color = "#e2e8f0"

    def _open_repo(self):
        webbrowser.open("https://github.com/example/fileforge")

    def _open_releases(self):
        webbrowser.open("https://github.com/example/fileforge/releases")

    def _check_updates_offline(self):
        QMessageBox.information(
            self,
            "Offline Update Manager",
            "FileForge is configured in Offline-First Mode.<br/><br/>"
            "To safeguard your data privacy, network telemetry calls are blocked. "
            "Please check for updates manually on the GitHub Releases tab."
        )
