from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QWidget, QFrame
from PyQt6.QtCore import Qt
from app.core.config import config

class OnboardingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to FileForge")
        self.resize(500, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        # Clean modal layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Style sheet to match main application style
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f1f5f9;
            }
            QLabel {
                color: #e2e8f0;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton#FinishBtn {
                background-color: #00f0ff;
                color: #090d16;
                border: none;
                font-weight: bold;
            }
            QPushButton#FinishBtn:hover {
                background-color: #33f3ff;
            }
        """)

        # Main slide stack
        self.stack = QStackedWidget()
        
        # Slide 1: Welcome
        slide1 = QWidget()
        s1_layout = QVBoxLayout(slide1)
        s1_layout.setSpacing(10)
        
        logo = QLabel("FileForge")
        logo.setStyleSheet("font-size: 32px; font-weight: bold; color: #00f0ff; margin-bottom: 5px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = QLabel(
            "Welcome to FileForge — a high-performance, offline-first intelligent "
            "file organizer, duplicates resolver, and storage analytics suite.<br/><br/>"
            "This application operates 100% offline. No cloud accounts, no trackers, "
            "no telemetry. Your data stays entirely on your local machine."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.5; color: #cbd5e1;")
        
        s1_layout.addWidget(logo)
        s1_layout.addWidget(desc)
        s1_layout.addStretch()
        self.stack.addWidget(slide1)

        # Slide 2: Scanning & Treemaps
        slide2 = QWidget()
        s2_layout = QVBoxLayout(slide2)
        s2_layout.setSpacing(10)
        
        title2 = QLabel("High-Speed Scanning & Map")
        title2.setStyleSheet("font-size: 20px; font-weight: bold; color: #00f0ff;")
        
        desc2 = QLabel(
            "<b>Multi-Threaded Traversal:</b> FileForge scans directory branches "
            "concurrently using optimized os.scandir calls, indexing millions of files in seconds.<br/><br/>"
            "<b>Squarified Treemap:</b> After scanning, files are rendered in an interactive "
            "nested storage map. Double-click folders to zoom, right-click to zoom out."
        )
        desc2.setWordWrap(True)
        desc2.setStyleSheet("font-size: 13px; line-height: 1.4;")
        
        s2_layout.addWidget(title2)
        s2_layout.addWidget(desc2)
        s2_layout.addStretch()
        self.stack.addWidget(slide2)

        # Slide 3: Safety & Rollbacks
        slide3 = QWidget()
        s3_layout = QVBoxLayout(slide3)
        s3_layout.setSpacing(10)
        
        title3 = QLabel("Beginner-Safe Cleanup Operations")
        title3.setStyleSheet("font-size: 20px; font-weight: bold; color: #00f0ff;")
        
        desc3 = QLabel(
            "<b>Windows Recycle Bin:</b> FileForge never hard-deletes files. "
            "All cleaning operations send files to the Windows Recycle Bin so they can be easily restored.<br/><br/>"
            "<b>Rollback Logs:</b> Moving or renaming files is fully tracked. "
            "If you make a mistake reorganizing folders, you can reverse the entire session "
            "with one click in the Recovery Center."
        )
        desc3.setWordWrap(True)
        desc3.setStyleSheet("font-size: 13px; line-height: 1.4;")
        
        s3_layout.addWidget(title3)
        s3_layout.addWidget(desc3)
        s3_layout.addStretch()
        self.stack.addWidget(slide3)

        layout.addWidget(self.stack)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.skip_btn = QPushButton("Skip")
        self.skip_btn.clicked.connect(self.accept)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._on_next_clicked)

        btn_layout.addWidget(self.skip_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

    def _on_next_clicked(self):
        curr_idx = self.stack.currentIndex()
        total_slides = self.stack.count()
        
        if curr_idx < total_slides - 1:
            self.stack.setCurrentIndex(curr_idx + 1)
            # If last page, change Next to Finish
            if curr_idx + 1 == total_slides - 1:
                self.next_btn.setText("Get Started")
                self.next_btn.setObjectName("FinishBtn")
                self.next_btn.setStyleSheet("") # Force stylesheet reload
        else:
            # Set settings onboarding flag to true and close
            config.set("onboarding_completed", True)
            self.accept()
