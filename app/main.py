import sys
import os
from PyQt6.QtWidgets import QApplication
from app.ui.window import MainWindow
from app.ui.views.onboarding import OnboardingDialog
from app.core.config import config

def main():
    # Windows specific scaling fixes
    if os.name == 'nt':
        # Enable high-DPI scaling support in Windows shells
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("FileForge")
    app.setApplicationVersion("1.0.0")

    # Launch MainWindow
    window = MainWindow()
    window.show()

    # Launch onboarding slideshow on first start
    if not config.get("onboarding_completed", False):
        dialog = OnboardingDialog(window)
        # Display modal blocked interaction window
        dialog.exec()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
