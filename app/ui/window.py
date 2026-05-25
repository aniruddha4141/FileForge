from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel, QStackedWidget, QMessageBox, QGroupBox, QLineEdit, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon
from app.ui.styles import get_stylesheet
from app.ui.resources import IconBuilder
from app.core.config import config
from app.ui.views.dashboard import DashboardView
from app.ui.views.scan import ScanView
from app.ui.views.cleanup import CleanupView
from app.ui.views.duplicates import DuplicatesView
from app.ui.views.search import SearchView
from app.ui.views.recovery import RecoveryView
from app.ui.views.about import AboutView
import os

class SettingsView(QWidget):
    """Clean settings view allowing exclusions customization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Exclusions Group
        ex_group = QGroupBox("System Scan Exclusions (Glob Patterns)")
        ex_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #1e293b; border-radius: 8px; margin-top: 10px; padding: 15px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        eg_layout = QVBoxLayout(ex_group)
        
        self.ex_list = QListWidget()
        self.ex_list.setStyleSheet("background-color: #111a2e; border: 1px solid #1e293b; border-radius: 6px;")
        self.load_exclusions()
        eg_layout.addWidget(self.ex_list)

        # Exclusions Inputs
        input_layout = QHBoxLayout()
        self.new_pattern = QLineEdit()
        self.new_pattern.setPlaceholderText("e.g. *.tmp, **/.vscode")
        
        self.add_btn = QPushButton("Add Pattern")
        self.add_btn.setObjectName("SecondaryButton")
        self.add_btn.clicked.connect(self._add_pattern)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setObjectName("SecondaryButton")
        self.remove_btn.clicked.connect(self._remove_pattern)

        input_layout.addWidget(self.new_pattern)
        input_layout.addWidget(self.add_btn)
        input_layout.addWidget(self.remove_btn)
        eg_layout.addLayout(input_layout)

        layout.addWidget(ex_group)

        # Info Group
        info_frame = QFrame()
        info_frame.setObjectName("CardFrame")
        if_layout = QVBoxLayout(info_frame)
        
        info_lbl = QLabel(
            "<b>FileForge v1.0.0 — Offline Storage Manager</b><br/>"
            "An optimized pair-programming desktop utility built for offline performance.<br/>"
            "License: MIT License<br/>"
            "Developer: DeepMind Advanced Agentic Coding"
        )
        info_lbl.setWordWrap(True)
        if_layout.addWidget(info_lbl)
        
        layout.addWidget(info_frame)
        layout.addStretch()

    def update_theme(self, theme: str):
        if theme == "light":
            self.ex_list.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; color: #0f172a;")
        else:
            self.ex_list.setStyleSheet("background-color: #111a2e; border: 1px solid #1e293b; border-radius: 6px; color: #e2e8f0;")

    def load_exclusions(self):
        self.ex_list.clear()
        exclusions = config.get("excluded_paths", [])
        for pattern in exclusions:
            self.ex_list.addItem(pattern)

    def _add_pattern(self):
        pat = self.new_pattern.text().strip()
        if pat:
            exclusions = config.get("excluded_paths", [])
            if pat not in exclusions:
                exclusions.append(pat)
                config.set("excluded_paths", exclusions)
                self.load_exclusions()
                self.new_pattern.clear()

    def _remove_pattern(self):
        curr = self.ex_list.currentItem()
        if curr:
            pat = curr.text()
            exclusions = config.get("excluded_paths", [])
            if pat in exclusions:
                exclusions.remove(pat)
                config.set("excluded_paths", exclusions)
                self.load_exclusions()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = config.get("theme", "dark")
        self.setWindowTitle("FileForge")
        self.resize(1100, 720)
        
        self._init_ui()
        self.apply_theme()
        
        # Load startup databases stats if scan records exist
        self._refresh_views_on_startup()

    def _init_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SidebarFrame")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(5)

        # App Title
        title_lbl = QLabel("FileForge")
        title_lbl.setObjectName("SidebarTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(title_lbl)

        # Sidebar Buttons Group
        self.nav_buttons = []
        self.views_indices = {}
        
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Scan Engine", "scan"),
            ("Cleanups", "cleanup"),
            ("Duplicates", "duplicates"),
            ("Local Search", "search"),
            ("Recovery Center", "recovery"),
            ("Settings", "settings"),
            ("About", "about")
        ]

        for idx, (lbl, icon_name) in enumerate(nav_items):
            btn = QPushButton(f"  {lbl}")
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            # Store metadata
            btn.setProperty("view_index", idx)
            btn.setProperty("icon_name", icon_name)
            btn.clicked.connect(self._on_navigation_clicked)
            
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            self.views_indices[icon_name] = idx

        # Set Dashboard active by default
        self.nav_buttons[0].setChecked(True)

        sidebar_layout.addStretch()

        # Theme Switcher Button at bottom of sidebar
        self.theme_btn = QPushButton(" Toggle Theme")
        self.theme_btn.setObjectName("SidebarButton")
        self.theme_btn.clicked.connect(self._toggle_theme_clicked)
        sidebar_layout.addWidget(self.theme_btn)
        
        # Spacer at bottom
        spacer = QLabel()
        spacer.setMinimumHeight(10)
        sidebar_layout.addWidget(spacer)

        main_layout.addWidget(self.sidebar)

        # 2. Main Area (Header + Stacked Pages Workspace)
        main_workspace = QFrame()
        main_workspace.setObjectName("WorkspaceFrame")
        workspace_layout = QVBoxLayout(main_workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # Top Header Frame
        self.header = QFrame()
        self.header.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.header_title = QLabel("STORAGE ANALYTICS DASHBOARD")
        self.header_title.setObjectName("HeaderTitle")
        header_layout.addWidget(self.header_title)
        
        workspace_layout.addWidget(self.header)

        # Stacked Views Widget
        self.stacked_widget = QStackedWidget()
        
        # Instantiate Subviews
        self.view_dashboard = DashboardView()
        self.view_scan = ScanView()
        self.view_cleanup = CleanupView()
        self.view_duplicates = DuplicatesView()
        self.view_search = SearchView()
        self.view_recovery = RecoveryView()
        self.view_settings = SettingsView()
        self.view_about = AboutView()

        # Wire Scan completion events
        self.view_scan.scan_completed.connect(self._on_scan_completed_sync)

        # Add to stack matching nav index order
        self.stacked_widget.addWidget(self.view_dashboard)
        self.stacked_widget.addWidget(self.view_scan)
        self.stacked_widget.addWidget(self.view_cleanup)
        self.stacked_widget.addWidget(self.view_duplicates)
        self.stacked_widget.addWidget(self.view_search)
        self.stacked_widget.addWidget(self.view_recovery)
        self.stacked_widget.addWidget(self.view_settings)
        self.stacked_widget.addWidget(self.view_about)

        workspace_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(main_workspace)

    def apply_theme(self):
        """Loads and applies the current theme QSS and updates procedural icons."""
        stylesheet = get_stylesheet(self.theme)
        self.setStyleSheet(stylesheet)

        # Set appropriate accent hex color based on theme
        accent = "#0066cc" if self.theme == "light" else "#00f0ff"
        text_col = "#64748b" if self.theme == "light" else "#94a3b8"

        # Redraw procedural icons on sidebar buttons
        for btn in self.nav_buttons:
            # Set dynamic icon color. Selected icon matches accent color.
            is_checked = btn.isChecked()
            color = accent if is_checked else text_col
            
            icon_name = btn.property("icon_name")
            btn.setIcon(IconBuilder.get_icon(icon_name, color, 18))

        # Adjust settings icon for theme toggle btn
        theme_icon = "scan" if self.theme == "light" else "dashboard" # sun/moon placeholder mappings
        self.theme_btn.setIcon(IconBuilder.get_icon("settings", text_col, 18))

        # Propagate theme changes to view painters
        self.view_dashboard.update_theme(self.theme)
        self.view_cleanup.update_theme(self.theme)
        self.view_duplicates.update_theme(self.theme)
        self.view_search.update_theme(self.theme)
        self.view_recovery.update_theme(self.theme)
        self.view_settings.update_theme(self.theme)
        self.view_scan.update_theme(self.theme)
        self.view_about.update_theme(self.theme)

    def _on_navigation_clicked(self):
        clicked_btn = self.sender()
        if not clicked_btn:
            return

        # Check only clicked button, uncheck rest
        for btn in self.nav_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
            else:
                btn.setChecked(True)

        target_idx = clicked_btn.property("view_index")
        self.stacked_widget.setCurrentIndex(target_idx)

        # Update Header Title
        title_lbl = clicked_btn.text().strip().upper()
        self.header_title.setText(title_lbl)

        # Dynamic subview loaders
        if target_idx == 0:  # Dashboard
            self.view_dashboard.refresh_stats()
        elif target_idx == 5:  # Recovery logs
            self.view_recovery.load_sessions()

        # Redraw sidebar icons colors
        self.apply_theme()

    def _toggle_theme_clicked(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        config.set("theme", self.theme)
        self.apply_theme()

    @pyqtSlot(str)
    def _on_scan_completed_sync(self, scanned_path: str):
        """Called automatically when crawler finishing to populate and switch to stats view."""
        # 1. Update stats across views
        self.view_dashboard.refresh_stats(scanned_path)
        
        # 2. Switch views back to dashboard page
        dashboard_idx = self.views_indices["dashboard"]
        
        # Uncheck other buttons, check dashboard button
        for idx, btn in enumerate(self.nav_buttons):
            btn.setChecked(idx == dashboard_idx)

        self.stacked_widget.setCurrentIndex(dashboard_idx)
        self.header_title.setText("DASHBOARD")
        
        self.apply_theme()

    def _refresh_views_on_startup(self):
        history = config.get("scan_history", [])
        if history and os.path.exists(history[0]):
            self.view_dashboard.refresh_stats(history[0])
            self.view_dashboard.update()
