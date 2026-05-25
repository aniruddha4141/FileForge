import os
from typing import List, Dict, Tuple, Any, Optional
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRectF, QPointF

class TreeNode:
    def __init__(self, path: str, size: int = 0):
        self.path = path
        self.name = os.path.basename(path) or path
        self.size = size
        self.children: Dict[str, 'TreeNode'] = {}
        self.is_file = False

    def add_child(self, path: str, size: int = 0) -> 'TreeNode':
        parts = Path(path).relative_to(Path(self.path)).parts
        current = self
        for part in parts:
            if part not in current.children:
                # Resolve full path of the part
                child_path = os.path.join(current.path, part)
                current.children[part] = TreeNode(child_path)
            current = current.children[part]
        current.size = size
        return current

class TreemapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_node: Optional[TreeNode] = None
        self.current_node: Optional[TreeNode] = None
        self.history: List[TreeNode] = []
        self.rects_map: List[Tuple[QRectF, TreeNode]] = []
        self.hovered_idx: int = -1
        
        # Style colors
        self.bg_color = QColor("#0d1527")
        self.border_color = QColor("#1e293b")
        self.accent_color = QColor("#00f0ff") # Cyberpunk cyan
        
        self.setMouseTracking(True)

    def set_data(self, root: TreeNode):
        """Loads a TreeNode structure into the widget."""
        self.root_node = root
        self.current_node = root
        self.history.clear()
        self.hovered_idx = -1
        self.rects_map.clear()
        self.update()

    def set_colors(self, bg_hex: str, border_hex: str, accent_hex: str):
        """Adapts widget colors dynamically based on active theme."""
        self.bg_color = QColor(bg_hex)
        self.border_color = QColor(border_hex)
        self.accent_color = QColor(accent_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        if not self.current_node or not self.current_node.children:
            # Draw placeholder when empty
            painter.setPen(self.border_color)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No folder scanned. Scan a drive to visualize space.")
            return

        # Prepare layout components
        children = list(self.current_node.children.values())
        # Sort children descending by size
        children.sort(key=lambda x: x.size, reverse=True)
        # Filter children with size > 0
        children = [c for c in children if c.size > 0]
        
        if not children:
            painter.setPen(self.border_color)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "All folder files are empty.")
            return
            
        total_size = sum(c.size for c in children)
        
        # Squarified layout boundary
        padding = 4.0
        boundary = QRectF(
            padding, padding, 
            float(self.width()) - 2 * padding, 
            float(self.height()) - 2 * padding
        )
        
        # Calculate Layout
        self.rects_map.clear()
        self._squarify(children, [], boundary, total_size)
        
        # Paint Rectangles
        for idx, (rect, node) in enumerate(self.rects_map):
            is_hovered = (idx == self.hovered_idx)
            
            painter.save()
            
            # Select background gradient based on index & hover state
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            
            # HSL based coloring to create matching but distinct colors
            hue = (idx * 37) % 360
            base_col = QColor.fromHsl(hue, 110, 45, 120)
            
            if is_hovered:
                # Bright highlight on hover
                grad.setColorAt(0.0, QColor.fromHsl(hue, 140, 60, 220))
                grad.setColorAt(1.0, QColor.fromHsl((hue + 20) % 360, 140, 50, 200))
                pen = QPen(self.accent_color, 2.0)
            else:
                grad.setColorAt(0.0, base_col)
                grad.setColorAt(1.0, QColor.fromHsl((hue + 20) % 360, 90, 35, 120))
                pen = QPen(self.border_color, 1.0)
                
            painter.setPen(pen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect, 4.0, 4.0)
            
            # Draw Labels inside blocks
            if rect.width() > 50 and rect.height() > 30:
                painter.setPen(QColor("#f8fafc"))
                font_size = min(11, max(8, int(rect.width() / 15)))
                painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
                
                # Show name and format size
                from app.utils.helpers import format_size
                text = f"{node.name}\n{format_size(node.size)}"
                painter.drawText(
                    rect.adjusted(5, 5, -5, -5), 
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.TextWordWrap, 
                    text
                )
                
            painter.restore()

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_hover = self.hovered_idx
        self.hovered_idx = -1
        
        for idx, (rect, node) in enumerate(self.rects_map):
            if rect.contains(pos):
                self.hovered_idx = idx
                
                # Update tooltip description
                from app.utils.helpers import format_size
                pct = (node.size / max(1, self.current_node.size)) * 100
                tooltip_txt = f"Path: {node.path}\nSize: {format_size(node.size)} ({pct:.1f}% of parent)"
                QToolTip.showText(event.globalPosition().toPoint(), tooltip_txt, self)
                break
                
        if self.hovered_idx != old_hover:
            self.update()

    def leaveEvent(self, event):
        self.hovered_idx = -1
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.hovered_idx != -1:
            _, selected_node = self.rects_map[self.hovered_idx]
            if selected_node.children:  # Zoom in only if it has sub-directories
                self.history.append(self.current_node)
                self.current_node = selected_node
                self.hovered_idx = -1
                self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Zoom out
            if self.history:
                self.current_node = self.history.pop()
                self.hovered_idx = -1
                self.update()

    # --- Squarification Layout Algorithm ---
    
    def _squarify(self, children: List[TreeNode], current_row: List[TreeNode], 
                  rect: QRectF, total_size: float):
        """Squarifies a list of layout nodes inside a boundary rectangle."""
        if not children:
            if current_row:
                self._layout_row(current_row, rect, total_size)
            return

        node = children[0]
        # Copy row and append node to test layout aspect ratio
        test_row = current_row + [node]
        
        # Check if adding this node improves or worsens worst aspect ratio
        if self._worst_aspect_ratio(current_row, rect, total_size) >= \
           self._worst_aspect_ratio(test_row, rect, total_size) or not current_row:
            # Aspect ratio improved or row was empty, keep item in current row
            self._squarify(children[1:], test_row, rect, total_size)
        else:
            # Aspect ratio got worse, freeze current row and calculate its geometry
            new_rect = self._layout_row(current_row, rect, total_size)
            # Layout the rest in the remaining canvas area
            self._squarify(children, [], new_rect, total_size)

    def _worst_aspect_ratio(self, row: List[TreeNode], rect: QRectF, total_size: float) -> float:
        """Returns the worst aspect ratio of row nodes scaled in a boundary rectangle."""
        if not row:
            return float('inf')
        
        sum_sizes = sum(node.size for node in row)
        if sum_sizes == 0:
            return float('inf')
            
        w = float(min(rect.width(), rect.height()))
        
        # Scale sizes to rectangle canvas coordinates
        scale = (rect.width() * rect.height()) / total_size
        
        min_size = min(node.size for node in row) * scale
        max_size = max(node.size for node in row) * scale
        row_area = sum_sizes * scale
        
        # Math formula for aspect ratio bounds
        val1 = (w**2 * max_size) / (row_area**2)
        val2 = (row_area**2) / (w**2 * min_size)
        return max(val1, val2)

    def _layout_row(self, row: List[TreeNode], rect: QRectF, total_size: float) -> QRectF:
        """Positions a finalized row inside the boundary, returning the remaining rectangle."""
        sum_sizes = sum(node.size for node in row)
        scale = (rect.width() * rect.height()) / total_size
        row_area = sum_sizes * scale
        
        is_vertical = rect.width() < rect.height()
        w = rect.width() if not is_vertical else rect.height()
        
        row_thickness = row_area / w if w > 0 else 0
        
        x = rect.x()
        y = rect.y()
        
        for node in row:
            node_area = node.size * scale
            node_length = node_area / row_thickness if row_thickness > 0 else 0
            
            if is_vertical:
                item_rect = QRectF(x, y, node_length, row_thickness)
                x += node_length
            else:
                item_rect = QRectF(x, y, row_thickness, node_length)
                y += node_length
                
            self.rects_map.append((item_rect, node))
            
        # Cut off placed row area and return remaining boundary
        if is_vertical:
            return QRectF(rect.x(), rect.y() + row_thickness, rect.width(), rect.height() - row_thickness)
        else:
            return QRectF(rect.x() + row_thickness, rect.y(), rect.width() - row_thickness, rect.height())

# Helper to build TreeNode structure from DB file paths
def build_tree_from_db(source_dir: str) -> TreeNode:
    """Queries SQLite for all files under a source directory, constructing a TreeNode hierarchy."""
    files = db.get_files_under_dir(source_dir)
    root = TreeNode(source_dir)
    
    # Track paths sizes
    folder_sizes: Dict[str, int] = {}
    
    for f in files:
        path = f["path"]
        size = f["size"]
        
        # Accumulate file size to all parent folders up to source_dir
        try:
            parent = os.path.dirname(path)
            while True:
                # Add folder size
                folder_sizes[parent] = folder_sizes.get(parent, 0) + size
                if parent == source_dir or len(Path(parent).parts) <= 1:
                    break
                parent = os.path.dirname(parent)
        except Exception:
            pass

    # Sort folders to construct tree leaf nodes first
    sorted_folders = sorted(folder_sizes.keys(), key=len)
    
    for folder in sorted_folders:
        if folder == source_dir:
            continue
        try:
            # Add subdirectory to tree structure
            root.add_child(folder, folder_sizes[folder])
        except Exception:
            pass
            
    # Load root size
    root.size = folder_sizes.get(source_dir, 0)
    
    return root
