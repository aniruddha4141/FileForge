from typing import List, Dict, Any, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF
from app.utils.helpers import format_size

class DonutChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[Dict[str, Any]] = []
        self.total_value: int = 0
        self.bg_color = QColor("#111a2e")
        self.text_color = QColor("#f1f5f9")

    def set_data(self, data: List[Dict[str, Any]]):
        """
        Accepts data list:
        [ {"label": "Images", "value": 102450}, {"label": "Documents", "value": 54100} ]
        """
        self.data = [d for d in data if d["value"] > 0]
        self.total_value = sum(d["value"] for d in self.data)
        self.update()

    def set_theme(self, bg_hex: str, text_hex: str):
        self.bg_color = QColor(bg_hex)
        self.text_color = QColor(text_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Background clearing
        painter.fillRect(self.rect(), self.bg_color)

        if not self.data or self.total_value == 0:
            painter.setPen(self.text_color)
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No category stats to display")
            return

        # Determine canvas boundaries (leaving space on the right for legend)
        chart_size = min(self.width() * 0.5, self.height() - 40.0)
        chart_rect = QRectF(20.0, (self.height() - chart_size) / 2.0, chart_size, chart_size)

        # Draw Donut Segments
        start_angle = 90 * 16  # start at 12 o'clock (angles in 1/16th degrees)
        
        for idx, item in enumerate(self.data):
            pct = item["value"] / self.total_value
            span_angle = int(-pct * 360 * 16)
            
            # Select HSL color for segment
            hue = (idx * 37) % 360
            color = QColor.fromHsl(hue, 120, 50)
            
            painter.save()
            # Draw segment border & fill
            painter.setPen(QPen(self.bg_color, 2.0))
            painter.setBrush(QBrush(color))
            painter.drawPie(chart_rect, start_angle, span_angle)
            painter.restore()
            
            start_angle += span_angle

        # Cover center with background color circle to form a Donut Chart
        donut_hole_size = chart_size * 0.6
        donut_hole_rect = QRectF(
            chart_rect.x() + (chart_size - donut_hole_size) / 2.0,
            chart_rect.y() + (chart_size - donut_hole_size) / 2.0,
            donut_hole_size,
            donut_hole_size
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.bg_color))
        painter.drawEllipse(donut_hole_rect)

        # Draw total size text in center of donut
        painter.setPen(self.text_color)
        font_val = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font_val)
        
        center_text_val = format_size(self.total_value)
        
        # Split text into size and unit/label
        painter.drawText(
            donut_hole_rect.adjusted(0, -10, 0, -10),
            Qt.AlignmentFlag.AlignCenter,
            center_text_val
        )
        
        font_lbl = QFont("Segoe UI", 8)
        painter.setFont(font_lbl)
        painter.drawText(
            donut_hole_rect.adjusted(0, 15, 0, 15),
            Qt.AlignmentFlag.AlignCenter,
            "Total Indexed"
        )

        # Draw Legend List on Right Panel
        legend_x = chart_rect.right() + 30.0
        legend_y = (self.height() - (len(self.data) * 22)) / 2.0
        
        painter.setFont(QFont("Segoe UI", 10))
        for idx, item in enumerate(self.data):
            hue = (idx * 37) % 360
            color = QColor.fromHsl(hue, 120, 50)
            
            # Color block
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(legend_x, legend_y + 4, 12, 12), 2, 2)
            
            # Text label
            painter.setPen(self.text_color)
            pct = (item["value"] / self.total_value) * 100
            label_text = f"{item['label']} — {format_size(item['value'])} ({pct:.1f}%)"
            painter.drawText(QPointF(legend_x + 20.0, legend_y + 14.0), label_text)
            
            legend_y += 22.0

class CategoryProgressBar(QWidget):
    """Draws a horizontal stacked bar showing distribution of categories."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[Dict[str, Any]] = []
        self.total_value: int = 0
        self.bg_color = QColor("#0d1527")

    def set_data(self, data: List[Dict[str, Any]]):
        self.data = [d for d in data if d["value"] > 0]
        self.total_value = sum(d["value"] for d in self.data)
        self.update()

    def set_theme(self, bg_hex: str):
        self.bg_color = QColor(bg_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        h = float(self.height())
        w = float(self.width())
        
        # Draw background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#1e293b")))
        painter.drawRoundedRect(QRectF(0, 0, w, h), 4.0, 4.0)

        if not self.data or self.total_value == 0:
            return

        current_x = 0.0
        for idx, item in enumerate(self.data):
            pct = item["value"] / self.total_value
            segment_w = pct * w
            
            hue = (idx * 37) % 360
            color = QColor.fromHsl(hue, 120, 50)
            
            painter.setBrush(QBrush(color))
            
            # Draw individual rounded corners or clipped rectangles
            # To draw simple segments:
            rect = QRectF(current_x, 0, segment_w, h)
            
            # Custom border rounding for edges
            if idx == 0 and len(self.data) == 1:
                painter.drawRoundedRect(rect, 4.0, 4.0)
            elif idx == 0:
                # Left rounding
                painter.drawRoundedRect(rect, 4.0, 4.0)
                # Overpaint right edge to keep it flat
                painter.drawRect(QRectF(current_x + 4.0, 0, segment_w - 4.0, h))
            elif idx == len(self.data) - 1:
                # Right rounding
                painter.drawRoundedRect(rect, 4.0, 4.0)
                # Overpaint left edge to keep it flat
                painter.drawRect(QRectF(current_x, 0, segment_w - 4.0, h))
            else:
                # Center flat rect
                painter.drawRect(rect)
                
            current_x += segment_w
