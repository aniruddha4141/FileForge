import os
import sys
import zipfile
import linecache
import tokenize
import io
import struct
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QProgressBar, QStackedWidget, QWidget, QCheckBox, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap, QIcon

class ExtractionWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, zip_bytes: bytes, target_dir: str):
        super().__init__()
        self.zip_bytes = zip_bytes
        self.target_dir = target_dir

    def run(self):
        try:
            os.makedirs(self.target_dir, exist_ok=True)
            
            with zipfile.ZipFile(io.BytesIO(self.zip_bytes)) as z:
                members = z.infolist()
                total = len(members)
                
                for idx, member in enumerate(members):
                    # Extract file
                    z.extract(member, self.target_dir)
                    # Report progress percentage
                    pct = int(((idx + 1) / total) * 100)
                    self.progress.emit(pct, f"Extracting: {member.filename}")
                    
            self.finished.emit(True, "Extraction completed successfully.")
        except Exception as e:
            self.finished.emit(False, str(e))

class InstallerDialog(QDialog):
    def __init__(self, zip_data: bytes):
        super().__init__()
        self.zip_data = zip_data
        self.install_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "FileForge")
        self.worker = None
        
        self.setWindowTitle("FileForge Setup Wizard")
        self.resize(500, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Style matching the FileForge Obsidian Dark aesthetic
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: "Segoe UI", sans-serif;
            }
            QLabel {
                color: #e2e8f0;
            }
            QLineEdit {
                background-color: #111a2e;
                color: #f1f5f9;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px;
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
            QPushButton#PrimaryBtn {
                background-color: #00f0ff;
                color: #090d16;
                border: none;
                font-weight: bold;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #33f3ff;
            }
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 6px;
                text-align: center;
                background-color: #0f172a;
                color: #f8fafc;
            }
            QProgressBar::chunk {
                background-color: #00f0ff;
                border-radius: 5px;
            }
        """)

        self.stack = QStackedWidget()

        # Slide 1: Welcome
        slide1 = QWidget()
        s1_layout = QVBoxLayout(slide1)
        s1_layout.setSpacing(10)
        
        # Load logo dynamically from zip
        self.logo_lbl = QLabel()
        logo_pix = self._get_logo_pixmap()
        if not logo_pix.isNull():
            self.logo_lbl.setPixmap(logo_pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.setWindowIcon(QIcon(logo_pix))
        else:
            self.logo_lbl.setText("🛠️")
            self.logo_lbl.setStyleSheet("font-size: 32px;")
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        logo = QLabel("FileForge Installer")
        logo.setStyleSheet("font-size: 28px; font-weight: bold; color: #00f0ff; margin-bottom: 5px;")
        desc = QLabel(
            "Welcome to the FileForge Setup Wizard.<br/><br/>"
            "This will install FileForge — High-Performance Storage Organizer on your computer.<br/><br/>"
            "Click Next to choose the installation folder."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; color: #cbd5e1; line-height: 1.4;")
        
        s1_layout.addWidget(self.logo_lbl)
        s1_layout.addWidget(logo)
        s1_layout.addWidget(desc)
        s1_layout.addStretch()
        self.stack.addWidget(slide1)

        # Slide 2: Folder Select
        slide2 = QWidget()
        s2_layout = QVBoxLayout(slide2)
        s2_layout.setSpacing(10)
        title2 = QLabel("Select Destination Location")
        title2.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f0ff;")
        desc2 = QLabel("Setup will install FileForge into the following folder. To install to a different folder, click Browse.")
        desc2.setWordWrap(True)
        
        path_row = QHBoxLayout()
        self.path_input = QLineEdit(self.install_dir)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        path_row.addWidget(self.path_input)
        path_row.addWidget(self.browse_btn)

        s2_layout.addWidget(title2)
        s2_layout.addWidget(desc2)
        s2_layout.addLayout(path_row)
        s2_layout.addStretch()
        self.stack.addWidget(slide2)

        # Slide 3: Installing
        slide3 = QWidget()
        s3_layout = QVBoxLayout(slide3)
        s3_layout.setSpacing(15)
        self.status_lbl = QLabel("Ready to install.")
        self.status_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.progress_bar = QProgressBar()
        s3_layout.addWidget(self.status_lbl)
        s3_layout.addWidget(self.progress_bar)
        s3_layout.addStretch()
        self.stack.addWidget(slide3)

        # Slide 4: Finished
        slide4 = QWidget()
        s4_layout = QVBoxLayout(slide4)
        s4_layout.setSpacing(10)
        title4 = QLabel("Completing FileForge Setup")
        title4.setStyleSheet("font-size: 22px; font-weight: bold; color: #00f0ff;")
        desc4 = QLabel("FileForge has been installed on your computer. Click Finish to exit Setup.")
        desc4.setWordWrap(True)
        
        self.chk_desktop = QCheckBox("Create Desktop Shortcut")
        self.chk_desktop.setChecked(True)
        self.chk_start_menu = QCheckBox("Create Start Menu Program Shortcut")
        self.chk_start_menu.setChecked(True)
        self.chk_launch = QCheckBox("Launch FileForge")
        self.chk_launch.setChecked(True)

        s4_layout.addWidget(title4)
        s4_layout.addWidget(desc4)
        s4_layout.addWidget(self.chk_desktop)
        s4_layout.addWidget(self.chk_start_menu)
        s4_layout.addWidget(self.chk_launch)
        s4_layout.addStretch()
        self.stack.addWidget(slide4)

        layout.addWidget(self.stack)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.back_btn = QPushButton("< Back")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self._on_back_clicked)
        
        self.next_btn = QPushButton("Next >")
        self.next_btn.setObjectName("PrimaryBtn")
        self.next_btn.clicked.connect(self._on_next_clicked)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.back_btn)
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.path_input.text())
        if folder:
            self.path_input.setText(os.path.normpath(folder))

    def _on_back_clicked(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self._update_navigation_buttons()

    def _on_next_clicked(self):
        curr = self.stack.currentIndex()
        
        if curr == 0:  # Welcome -> Dir Select
            self.stack.setCurrentIndex(1)
            self._update_navigation_buttons()
            
        elif curr == 1:  # Dir Select -> Extracting Progress
            self.install_dir = self.path_input.text().strip()
            if not self.install_dir:
                return
                
            self.stack.setCurrentIndex(2)
            self._update_navigation_buttons()
            self._start_installation()
            
        elif curr == 3:  # Finished -> Exit
            self._create_shortcuts_and_finish()

    def _update_navigation_buttons(self):
        curr = self.stack.currentIndex()
        self.back_btn.setEnabled(curr in (1, 2))
        self.cancel_btn.setEnabled(curr != 3) # Can't cancel once finished
        
        if curr == 2:
            self.next_btn.setEnabled(False)
            self.back_btn.setEnabled(False)
        elif curr == 3:
            self.next_btn.setText("Finish")
            self.next_btn.setEnabled(True)
            self.back_btn.setEnabled(False)
        else:
            self.next_btn.setText("Next >")
            self.next_btn.setEnabled(True)

    def _start_installation(self):
        self.status_lbl.setText("Extracting application package...")
        self.progress_bar.setValue(0)
        
        self.worker = ExtractionWorker(self.zip_data, self.install_dir)
        self.worker.progress.connect(self._on_extraction_progress)
        self.worker.finished.connect(self._on_extraction_finished)
        self.worker.start()

    @pyqtSlot(int, str)
    def _on_extraction_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        # Display current file name
        short_msg = msg[:60] + "..." if len(msg) > 60 else msg
        self.status_lbl.setText(short_msg)

    @pyqtSlot(bool, str)
    def _on_extraction_finished(self, ok: bool, msg: str):
        if ok:
            self.stack.setCurrentIndex(3)
            self._update_navigation_buttons()
        else:
            self.status_lbl.setText("Installation Failed!")
            QMessageBox.critical(self, "Installation Error", f"Failed to extract files:\n{msg}")
            self.reject()

    def _create_shortcuts_and_finish(self):
        target_exe = os.path.join(self.install_dir, "FileForge.exe")
        
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            
            # 1. Desktop Shortcut
            if self.chk_desktop.isChecked():
                desktop_dir = shell.SpecialFolders("Desktop")
                shortcut_path = os.path.join(desktop_dir, "FileForge.lnk")
                
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = target_exe
                shortcut.WorkingDirectory = self.install_dir
                shortcut.Description = "FileForge — High-Performance Storage Organizer"
                shortcut.save()

            # 2. Start Menu Shortcut
            if self.chk_start_menu.isChecked():
                start_menu_dir = shell.SpecialFolders("Programs")
                shortcut_path = os.path.join(start_menu_dir, "FileForge.lnk")
                
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = target_exe
                shortcut.WorkingDirectory = self.install_dir
                shortcut.Description = "FileForge — High-Performance Storage Organizer"
                shortcut.save()
        except Exception as e:
            print(f"Failed to create shortcuts: {e}")

        # 3. Launch application
        if self.chk_launch.isChecked() and os.path.exists(target_exe):
            try:
                os.startfile(target_exe)
            except Exception as e:
                print(f"Failed to launch FileForge: {e}")

        self.accept()

    def _get_logo_pixmap(self) -> QPixmap:
        try:
            with zipfile.ZipFile(io.BytesIO(self.zip_data)) as z:
                for name in z.namelist():
                    if name.endswith("logo.png"):
                        data = z.read(name)
                        pix = QPixmap()
                        pix.loadFromData(data)
                        return pix
        except Exception as e:
            print(f"Failed to load logo from zip: {e}")
        return QPixmap()

def get_payload_zip() -> bytes:
    """Reads the appended ZIP payload from the compiled exe binary or local payload.zip."""
    exe_path = sys.executable
    
    # Debug mode running under Python interpreter
    if exe_path.lower().endswith("python.exe") or exe_path.lower().endswith("pythonw.exe"):
        zip_path = os.path.join(os.path.dirname(__file__), "payload.zip")
        if os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                return f.read()
        return b""
        
    # Production compiled mode: read payload from sys.executable footer
    try:
        with open(exe_path, "rb") as f:
            f.seek(-8, 2)  # Read last 8 bytes for zip size
            zip_size_bytes = f.read(8)
            zip_size = struct.unpack("<Q", zip_size_bytes)[0]
            
            # Seek back to zip payload start
            f.seek(-(8 + zip_size), 2)
            return f.read(zip_size)
    except Exception as e:
        print(f"Error reading installer zip payload: {e}")
        return b""

def main():
    app = QApplication(sys.argv)
    zip_bytes = get_payload_zip()
    
    if not zip_bytes:
        print("Error: No zip installer payload found! Installer cannot run.")
        sys.exit(1)
        
    dialog = InstallerDialog(zip_bytes)
    dialog.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
