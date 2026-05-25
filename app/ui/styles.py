# QSS Stylesheets for FileForge

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0b0f19;
    color: #f1f5f9;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, sans-serif;
}

/* Left Sidebar styling */
#SidebarFrame {
    background-color: #0d1527;
    border-right: 1px solid #1e293b;
    min-width: 220px;
    max-width: 220px;
}

#SidebarTitle {
    color: #00f0ff;
    font-size: 20px;
    font-weight: bold;
    padding: 20px 10px;
}

#SidebarButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 6px;
    padding: 10px 15px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}

#SidebarButton:hover {
    background-color: #1e293b;
    color: #f1f5f9;
}

#SidebarButton:checked {
    background-color: #1e293b;
    color: #00f0ff;
    border-left: 3px solid #00f0ff;
    border-radius: 0px 6px 6px 0px;
}

/* Header styling */
#HeaderFrame {
    background-color: #0d1527;
    border-bottom: 1px solid #1e293b;
    min-height: 60px;
}

#HeaderTitle {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 600;
}

/* Main workspace panel */
#WorkspaceFrame {
    background-color: #0b0f19;
}

/* Cards & Containers */
QFrame#CardFrame {
    background-color: #111a2e;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 15px;
}

QLabel {
    color: #e2e8f0;
}

QLabel#CardTitle {
    font-size: 14px;
    color: #94a3b8;
    font-weight: bold;
}

QLabel#CardValue {
    font-size: 24px;
    color: #f8fafc;
    font-weight: bold;
}

/* Input Fields */
QLineEdit {
    background-color: #111a2e;
    color: #f1f5f9;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid #00f0ff;
}

/* Buttons */
QPushButton#PrimaryButton {
    background-color: #00f0ff;
    color: #090d16;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 14px;
}

QPushButton#PrimaryButton:hover {
    background-color: #33f3ff;
}

QPushButton#PrimaryButton:pressed {
    background-color: #00c8d6;
}

QPushButton#SecondaryButton {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 14px;
}

QPushButton#SecondaryButton:hover {
    background-color: #334155;
}

QPushButton#IconButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
}

QPushButton#IconButton:hover {
    background-color: #1e293b;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Virtual Table Styling */
QTableView {
    background-color: #111a2e;
    color: #f1f5f9;
    border: 1px solid #1e293b;
    border-radius: 8px;
    gridline-color: #1e293b;
    selection-background-color: #1e293b;
    selection-color: #00f0ff;
    font-size: 13px;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: bold;
}

QTableView QTableCornerButton::section {
    background-color: #0f172a;
    border: none;
}

/* Tab Widgets */
QTabWidget::pane {
    border: 1px solid #1e293b;
    background-color: #111a2e;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #0d1527;
    color: #94a3b8;
    border: 1px solid #1e293b;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background-color: #111a2e;
    color: #00f0ff;
    border-bottom: 1px solid #111a2e;
}

QTabBar::tab:hover:!selected {
    background-color: #1e293b;
    color: #f1f5f9;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #1e293b;
    border-radius: 6px;
    text-align: center;
    background-color: #0f172a;
    color: #f8fafc;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #00f0ff;
    border-radius: 5px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, sans-serif;
}

/* Left Sidebar styling */
#SidebarFrame {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
    min-width: 220px;
    max-width: 220px;
}

#SidebarTitle {
    color: #0066cc;
    font-size: 20px;
    font-weight: bold;
    padding: 20px 10px;
}

#SidebarButton {
    background-color: transparent;
    color: #64748b;
    border: none;
    border-radius: 6px;
    padding: 10px 15px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}

#SidebarButton:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

#SidebarButton:checked {
    background-color: #f1f5f9;
    color: #0066cc;
    border-left: 3px solid #0066cc;
    border-radius: 0px 6px 6px 0px;
}

/* Header styling */
#HeaderFrame {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    min-height: 60px;
}

#HeaderTitle {
    color: #0f172a;
    font-size: 18px;
    font-weight: 600;
}

/* Main workspace panel */
#WorkspaceFrame {
    background-color: #f8fafc;
}

/* Cards & Containers */
QFrame#CardFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 15px;
}

QLabel {
    color: #334155;
}

QLabel#CardTitle {
    font-size: 14px;
    color: #64748b;
    font-weight: bold;
}

QLabel#CardValue {
    font-size: 24px;
    color: #0f172a;
    font-weight: bold;
}

/* Input Fields */
QLineEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid #0066cc;
}

/* Buttons */
QPushButton#PrimaryButton {
    background-color: #0066cc;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 14px;
}

QPushButton#PrimaryButton:hover {
    background-color: #1d4ed8;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1e3a8a;
}

QPushButton#SecondaryButton {
    background-color: #f1f5f9;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 14px;
}

QPushButton#SecondaryButton:hover {
    background-color: #e2e8f0;
}

QPushButton#IconButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
}

QPushButton#IconButton:hover {
    background-color: #f1f5f9;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Table Styling */
QTableView {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #f1f5f9;
    selection-color: #0066cc;
    font-size: 13px;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-weight: bold;
}

QTableView QTableCornerButton::section {
    background-color: #f8fafc;
    border: none;
}

/* Tab Widgets */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #f8fafc;
    color: #64748b;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0066cc;
    border-bottom: 1px solid #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #f1f5f9;
    color: #0f172a;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    text-align: center;
    background-color: #f1f5f9;
    color: #334155;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #0066cc;
    border-radius: 5px;
}
"""

def get_stylesheet(theme_name: str) -> str:
    """Returns the QSS stylesheet string for the requested theme."""
    if theme_name == "light":
        return LIGHT_THEME_QSS
    return DARK_THEME_QSS
