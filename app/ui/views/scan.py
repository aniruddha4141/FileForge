from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame, QProgressBar, QFileDialog
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from app.scanning.crawler import FileScanner
from app.core.config import config
from app.indexing.db import db
from app.utils.helpers import format_size, format_datetime
import time

class ScanView(QWidget):
    # Signals to notify main window
    scan_started = pyqtSignal(str)
    scan_completed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = None
        self.scanned_dir = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Drive / Directory Selector
        selector_frame = QFrame()
        selector_frame.setObjectName("CardFrame")
        sf_layout = QHBoxLayout(selector_frame)
        sf_layout.setContentsMargins(10, 10, 10, 10)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select drive or folder to scan...")
        
        # Load last scanned dir as default if exists
        history = config.get("scan_history", [])
        if history:
            self.path_input.setText(history[0])

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("SecondaryButton")
        self.browse_btn.clicked.connect(self._on_browse_clicked)

        self.start_btn = QPushButton("Start Scan")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self._on_start_clicked)

        sf_layout.addWidget(self.path_input)
        sf_layout.addWidget(self.browse_btn)
        sf_layout.addWidget(self.start_btn)
        layout.addWidget(selector_frame)

        # 2. Scanning Progress Frame
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("CardFrame")
        pf_layout = QVBoxLayout(self.progress_frame)
        pf_layout.setSpacing(15)

        # Title / Status
        self.status_lbl = QLabel("Ready to scan.")
        self.status_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #00f0ff;")
        pf_layout.addWidget(self.status_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        pf_layout.addWidget(self.progress_bar)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("SecondaryButton")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

        ctrl_layout.addWidget(self.pause_btn)
        ctrl_layout.addWidget(self.cancel_btn)
        ctrl_layout.addStretch()
        pf_layout.addLayout(ctrl_layout)

        layout.addWidget(self.progress_frame)

        # 3. Statistics Grid Card
        stats_frame = QFrame()
        stats_frame.setObjectName("CardFrame")
        stats_layout = QVBoxLayout(stats_frame)
        stats_title = QLabel("CRAWLING ENGINE REAL-TIME STATISTICS")
        stats_title.setObjectName("CardTitle")
        stats_layout.addWidget(stats_title)

        stats_grid = QHBoxLayout()
        
        # Files card
        f_lbl_frame = QFrame()
        f_lbl_layout = QVBoxLayout(f_lbl_frame)
        f_lbl = QLabel("Files Indexed")
        f_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.files_cnt_lbl = QLabel("0")
        self.files_cnt_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")
        f_lbl_layout.addWidget(f_lbl)
        f_lbl_layout.addWidget(self.files_cnt_lbl)
        stats_grid.addWidget(f_lbl_frame)

        # Folders card
        fol_lbl_frame = QFrame()
        fol_lbl_layout = QVBoxLayout(fol_lbl_frame)
        fol_lbl = QLabel("Folders Crawled")
        fol_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.folders_cnt_lbl = QLabel("0")
        self.folders_cnt_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")
        fol_lbl_layout.addWidget(fol_lbl)
        fol_lbl_layout.addWidget(self.folders_cnt_lbl)
        stats_grid.addWidget(fol_lbl_frame)

        # Size card
        sz_lbl_frame = QFrame()
        sz_lbl_layout = QVBoxLayout(sz_lbl_frame)
        sz_lbl = QLabel("Total Size")
        sz_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.size_cnt_lbl = QLabel("0 Bytes")
        self.size_cnt_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")
        sz_lbl_layout.addWidget(sz_lbl)
        sz_lbl_layout.addWidget(self.size_cnt_lbl)
        stats_grid.addWidget(sz_lbl_frame)

        # Speed card
        sp_lbl_frame = QFrame()
        sp_lbl_layout = QVBoxLayout(sp_lbl_frame)
        sp_lbl = QLabel("Speed")
        sp_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.speed_lbl = QLabel("0 files/s")
        self.speed_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")
        sp_lbl_layout.addWidget(sp_lbl)
        sp_lbl_layout.addWidget(self.speed_lbl)
        stats_grid.addWidget(sp_lbl_frame)

        stats_layout.addLayout(stats_grid)
        layout.addWidget(stats_frame)
        layout.addStretch()

    def update_theme(self, theme: str):
        if theme == "light":
            self.status_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0066cc;")
            for lbl in [self.files_cnt_lbl, self.folders_cnt_lbl, self.size_cnt_lbl, self.speed_lbl]:
                lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0f172a;")
        else:
            self.status_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #00f0ff;")
            for lbl in [self.files_cnt_lbl, self.folders_cnt_lbl, self.size_cnt_lbl, self.speed_lbl]:
                lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")

    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self.path_input.setText(folder)

    def _on_start_clicked(self):
        target = self.path_input.text().strip()
        if not target:
            self.status_lbl.setText("Error: Select a path to scan first.")
            return

        # Clear database to perform fresh scan
        db.clear_database()
        
        self.scanned_dir = target
        config.add_to_history(target)
        
        # UI updates
        self.start_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.path_input.setEnabled(False)
        
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.pause_btn.setText("Pause")
        
        # Progress bar to indeterminate mode (crawling directory size)
        self.progress_bar.setRange(0, 0)
        self.status_lbl.setText("Scoping filesystem boundaries...")
        
        # Get exclusions patterns from settings
        exclusions = config.get("excluded_paths", [])

        # Start Crawler Thread
        self.scanner = FileScanner([target], excluded_patterns=exclusions)
        self.scanner.progress_updated.connect(self._on_scan_progress)
        self.scanner.scan_finished.connect(self._on_scan_finished)
        self.scanner.scan_error.connect(self._on_scan_error)
        
        self.scan_started.emit(target)
        self.scanner.start()

    @pyqtSlot(dict)
    def _on_scan_progress(self, stats: dict):
        self.files_cnt_lbl.setText(f"{stats['files_scanned']:,}")
        self.folders_cnt_lbl.setText(f"{stats['folders_scanned']:,}")
        self.size_cnt_lbl.setText(format_size(stats['bytes_scanned']))
        
        speed = stats['speed']
        self.speed_lbl.setText(f"{int(speed):,} files/s")
        
        elapsed = stats['elapsed']
        self.status_lbl.setText(f"Scanning directory hierarchy... ({elapsed:.1f}s)")

    @pyqtSlot(dict)
    def _on_scan_finished(self, summary: dict):
        # Scan complete
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        is_cancel = summary.get("is_cancelled", False)
        
        if is_cancel:
            self.status_lbl.setText("Scan cancelled by user.")
        else:
            self.status_lbl.setText(f"Scan complete. Indexed {summary['total_files']:,} files in {summary['elapsed']:.2f} seconds.")

        # Re-enable UI
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.path_input.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        # Notify main shell
        self.scan_completed.emit(self.scanned_dir)

    @pyqtSlot(str)
    def _on_scan_error(self, err_msg: str):
        self.status_lbl.setText(f"Scan error: {err_msg}")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.path_input.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

    def _on_pause_clicked(self):
        if not self.scanner:
            return
            
        if self.scanner.is_paused:
            self.scanner.resume()
            self.pause_btn.setText("Pause")
            self.status_lbl.setText("Scanning directory hierarchy...")
        else:
            self.scanner.pause()
            self.pause_btn.setText("Resume")
            self.status_lbl.setText("Scanning paused by user.")

    def _on_cancel_clicked(self):
        if self.scanner:
            self.status_lbl.setText("Cancelling scanning thread...")
            self.scanner.cancel()
