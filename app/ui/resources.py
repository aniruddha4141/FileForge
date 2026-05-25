from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QPointF, QRectF

class IconBuilder:
    @staticmethod
    def create_pixmap(name: str, color_hex: str, size: int = 24) -> QPixmap:
        """Draws procedural vector icons using QPainter."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(color_hex)
        pen = QPen(color)
        pen.setWidthF(2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Scaling factor based on standard size of 24
        scale = size / 24.0
        
        if name == "dashboard":
            # Draw a grid dashboard dashboard icon (four rounded squares)
            for x, y in [(3, 3), (13, 3), (3, 13), (13, 13)]:
                r = QRectF(x * scale, y * scale, 8 * scale, 8 * scale)
                painter.drawRoundedRect(r, 2 * scale, 2 * scale)
                
        elif name == "scan":
            # Draw a folder with a magnifying glass
            # Folder outline
            path = QPainterPath()
            path.moveTo(2 * scale, 5 * scale)
            path.lineTo(8 * scale, 5 * scale)
            path.lineTo(10 * scale, 8 * scale)
            path.lineTo(21 * scale, 8 * scale)
            path.lineTo(21 * scale, 19 * scale)
            path.lineTo(2 * scale, 19 * scale)
            path.closeSubpath()
            painter.drawPath(path)
            # Glass handle & circle
            cx, cy, r = 16 * scale, 13 * scale, 3 * scale
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawLine(QPointF(cx + 2 * scale, cy + 2 * scale), QPointF(20 * scale, 17 * scale))

        elif name == "cleanup":
            # Draw a broom / brush or a trash bin
            # Trash bin
            painter.drawRoundedRect(QRectF(5 * scale, 6 * scale, 14 * scale, 15 * scale), 2 * scale, 2 * scale)
            painter.drawLine(QPointF(3 * scale, 6 * scale), QPointF(21 * scale, 6 * scale))  # Lid line
            painter.drawRoundedRect(QRectF(9 * scale, 3 * scale, 6 * scale, 3 * scale), 1 * scale, 1 * scale)  # Handle
            # Lines inside bin
            painter.drawLine(QPointF(9 * scale, 10 * scale), QPointF(9 * scale, 17 * scale))
            painter.drawLine(QPointF(12 * scale, 10 * scale), QPointF(12 * scale, 17 * scale))
            painter.drawLine(QPointF(15 * scale, 10 * scale), QPointF(15 * scale, 17 * scale))

        elif name == "duplicates":
            # Two overlapping cards/sheets
            painter.drawRoundedRect(QRectF(3 * scale, 3 * scale, 12 * scale, 12 * scale), 2 * scale, 2 * scale)
            # Second card overlapping
            painter.setBrush(QBrush(QColor("#0d1527"))) # Opaque background so line is hidden
            if color_hex == "#0066cc": # Light mode background
                painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRoundedRect(QRectF(9 * scale, 9 * scale, 12 * scale, 12 * scale), 2 * scale, 2 * scale)
            
        elif name == "analytics":
            # Simple bar chart (three bars)
            painter.drawRoundedRect(QRectF(3 * scale, 14 * scale, 4 * scale, 7 * scale), 1 * scale, 1 * scale)
            painter.drawRoundedRect(QRectF(10 * scale, 8 * scale, 4 * scale, 13 * scale), 1 * scale, 1 * scale)
            painter.drawRoundedRect(QRectF(17 * scale, 3 * scale, 4 * scale, 18 * scale), 1 * scale, 1 * scale)
            
        elif name == "search":
            # Magnifying glass
            painter.drawEllipse(QPointF(10 * scale, 10 * scale), 6 * scale, 6 * scale)
            painter.drawLine(QPointF(14.5 * scale, 14.5 * scale), QPointF(21 * scale, 21 * scale))
            
        elif name == "recovery":
            # Anti-clockwise circle arrow
            painter.drawArc(QRectF(4 * scale, 4 * scale, 16 * scale, 16 * scale), int(-30 * 16), int(300 * 16))
            # Arrowhead
            arrow = QPainterPath()
            arrow.moveTo(16 * scale, 4 * scale)
            arrow.lineTo(20 * scale, 5 * scale)
            arrow.lineTo(17 * scale, 9 * scale)
            painter.drawPath(arrow)
            
        elif name == "settings":
            # Gear
            painter.drawEllipse(QPointF(12 * scale, 12 * scale), 4 * scale, 4 * scale)
            # Gear spokes
            for angle in range(0, 360, 45):
                painter.save()
                painter.translate(12 * scale, 12 * scale)
                painter.rotate(angle)
                painter.drawLine(QPointF(0, -6 * scale), QPointF(0, -9 * scale))
                painter.restore()
                
        elif name == "about":
            # Circular Info Icon (circle + dot + line)
            painter.drawEllipse(QPointF(12 * scale, 12 * scale), 9 * scale, 9 * scale)
            # Dot of the i
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(12 * scale, 8 * scale), 1 * scale, 1 * scale)
            # Body of the i
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(12 * scale, 11 * scale), QPointF(12 * scale, 16 * scale))
            
        else:
            # Draw generic circle dot
            painter.drawEllipse(QPointF(12 * scale, 12 * scale), 5 * scale, 5 * scale)
            
        painter.end()
        return pixmap

    @classmethod
    def get_icon(cls, name: str, color_hex: str, size: int = 24) -> QIcon:
        """Returns a QIcon matching the procedural design and theme color."""
        return QIcon(cls.create_pixmap(name, color_hex, size))
