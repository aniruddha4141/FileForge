from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from app.utils.helpers import format_size, format_datetime

class FileTableModel(QAbstractTableModel):
    COLUMNS = ["Name", "Category", "Size", "Date Modified", "Path"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files_data: List[Dict[str, Any]] = []

    def set_files(self, files: List[Dict[str, Any]]):
        """Loads a list of file dictionaries from the database."""
        self.beginResetModel()
        self.files_data = files
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.files_data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self.files_data)):
            return None

        file_rec = self.files_data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:  # Name
                return file_rec["name"]
            elif col == 1:  # Category
                return file_rec["category"]
            elif col == 2:  # Size
                return format_size(file_rec["size"])
            elif col == 3:  # Date Modified
                return format_datetime(file_rec["modified_at"])
            elif col == 4:  # Path
                return file_rec["path"]

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (1, 2, 3):  # Center align Category, Size, Date
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.UserRole:
            # Custom role for returning raw file dictionary
            return file_rec

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sorts table data based on column clicked."""
        if not self.files_data:
            return

        self.layoutAboutToBeChanged.emit()

        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        # Sort based on underlying raw database types
        if column == 0:  # Name
            self.files_data.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        elif column == 1:  # Category
            self.files_data.sort(key=lambda x: x["category"].lower(), reverse=reverse)
        elif column == 2:  # Size
            self.files_data.sort(key=lambda x: x["size"], reverse=reverse)
        elif column == 3:  # Date Modified
            self.files_data.sort(key=lambda x: x["modified_at"], reverse=reverse)
        elif column == 4:  # Path
            self.files_data.sort(key=lambda x: x["path"].lower(), reverse=reverse)

        self.layoutChanged.emit()
