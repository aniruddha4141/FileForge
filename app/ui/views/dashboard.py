from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSplitter, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSlot
from app.indexing.db import db
from app.ui.widgets.charts import DonutChartWidget
from app.ui.widgets.treemap import TreemapWidget, build_tree_from_db
from app.utils.helpers import format_size, format_datetime
import os

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_scanned_dir = ""
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 1. Top Cards Row (Stats Summary)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        # Health Card
        self.health_card = QFrame()
        self.health_card.setObjectName("CardFrame")
        hc_layout = QVBoxLayout(self.health_card)
        hc_title = QLabel("STORAGE HEALTH")
        hc_title.setObjectName("CardTitle")
        self.hc_val = QLabel("100% - Excellent")
        self.hc_val.setObjectName("CardValue")
        hc_layout.addWidget(hc_title)
        hc_layout.addWidget(self.hc_val)
        cards_layout.addWidget(self.health_card)

        # Total Indexed Card
        self.size_card = QFrame()
        self.size_card.setObjectName("CardFrame")
        sc_layout = QVBoxLayout(self.size_card)
        sc_title = QLabel("TOTAL SIZE INDEXED")
        sc_title.setObjectName("CardTitle")
        self.sc_val = QLabel("0 Bytes")
        self.sc_val.setObjectName("CardValue")
        sc_layout.addWidget(sc_title)
        sc_layout.addWidget(self.sc_val)
        cards_layout.addWidget(self.size_card)

        # Reclaimable Card
        self.reclaim_card = QFrame()
        self.reclaim_card.setObjectName("CardFrame")
        rc_layout = QVBoxLayout(self.reclaim_card)
        rc_title = QLabel("RECLAIMABLE SPACE")
        rc_title.setObjectName("CardTitle")
        self.rc_val = QLabel("0 Bytes")
        self.rc_val.setObjectName("CardValue")
        rc_layout.addWidget(rc_title)
        rc_layout.addWidget(self.rc_val)
        cards_layout.addWidget(self.reclaim_card)

        main_layout.addLayout(cards_layout)

        # 2. Main Analytics Workspace (Splitter for Chart & Treemap)
        workspace_splitter = QSplitter(Qt.Orientation.Vertical)
        workspace_splitter.setChildrenCollapsible(False)

        # Top section: Donut Chart & Largest Files side-by-side
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setChildrenCollapsible(False)

        # Donut Panel
        donut_frame = QFrame()
        donut_frame.setObjectName("CardFrame")
        donut_layout = QVBoxLayout(donut_frame)
        donut_title = QLabel("Category Distribution")
        donut_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #94a3b8;")
        self.donut_chart = DonutChartWidget()
        donut_layout.addWidget(donut_title)
        donut_layout.addWidget(self.donut_chart)
        top_splitter.addWidget(donut_frame)

        # Largest Files Panel
        files_frame = QFrame()
        files_frame.setObjectName("CardFrame")
        files_layout = QVBoxLayout(files_frame)
        files_title = QLabel("Largest Files Indexed")
        files_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #94a3b8;")
        self.largest_list = QListWidget()
        self.largest_list.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #e2e8f0;")
        files_layout.addWidget(files_title)
        files_layout.addWidget(self.largest_list)
        top_splitter.addWidget(files_frame)

        workspace_splitter.addWidget(top_splitter)

        # Bottom section: Interactive Treemap
        treemap_frame = QFrame()
        treemap_frame.setObjectName("CardFrame")
        treemap_layout = QVBoxLayout(treemap_frame)
        treemap_title = QLabel("Interactive Storage Map (Double-click folder block to zoom, Right-click to zoom out)")
        treemap_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #94a3b8;")
        self.treemap = TreemapWidget()
        treemap_layout.addWidget(treemap_title)
        treemap_layout.addWidget(self.treemap)
        
        workspace_splitter.addWidget(treemap_frame)
        
        # Set proportions: Top section 45%, Treemap 55%
        workspace_splitter.setSizes([350, 450])

        main_layout.addWidget(workspace_splitter)

    def update_theme(self, theme: str):
        """Forces widgets colors updates matching theme."""
        if theme == "light":
            self.donut_chart.set_theme("#ffffff", "#0f172a")
            self.treemap.set_colors("#ffffff", "#cbd5e1", "#0066cc")
        else:
            self.donut_chart.set_theme("#111a2e", "#f1f5f9")
            self.treemap.set_colors("#111a2e", "#1e293b", "#00f0ff")

    @pyqtSlot()
    def refresh_stats(self, scanned_path: str = ""):
        """Queries database and rebuilds all dashboard widgets."""
        if scanned_path:
            self.last_scanned_dir = scanned_path

        summary = db.get_scanned_summary()
        total_files = summary["total_files"]
        total_size = summary["total_size"]

        if total_files == 0:
            self.sc_val.setText("0 Bytes")
            self.rc_val.setText("0 Bytes")
            self.hc_val.setText("100% - Excellent")
            self.largest_list.clear()
            self.donut_chart.set_data([])
            return

        # 1. Update Cards values
        self.sc_val.setText(format_size(total_size))
        
        # Calculate reclaimable space:
        # We check duplicate file sizes + temp file categories + developer leftovers size
        # Query total duplicates size (sum size of duplicates minus one representation)
        duplicate_sizes = db.get_duplicate_size_groups(1024)
        dup_reclaimable = 0
        for size in duplicate_sizes:
            files = db.get_files_by_size(size)
            if len(files) > 1:
                dup_reclaimable += size * (len(files) - 1)
                
        # Query temp size
        category_stats = db.get_category_stats()
        temp_size = 0
        donut_data = []
        for stat in category_stats:
            cat = stat["category"]
            sz = stat["total_size"]
            if cat == "Temp/Cache":
                temp_size += sz
            donut_data.append({"label": cat, "value": sz})

        total_reclaimable = dup_reclaimable + temp_size
        self.rc_val.setText(format_size(total_reclaimable))

        # Calculate Storage Health Score
        # Deduction based on duplicate and junk ratios
        health = 100
        if total_size > 0:
            dup_ratio = dup_reclaimable / total_size
            temp_ratio = temp_size / total_size
            
            # Deduct health based on ratios
            deduction = int((dup_ratio * 50) + (temp_ratio * 50))
            health = max(10, 100 - deduction)

        if health >= 90:
            self.hc_val.setText(f"{health}% — Excellent")
            self.hc_val.setStyleSheet("color: #10b981;") # emerald green
        elif health >= 75:
            self.hc_val.setText(f"{health}% — Healthy")
            self.hc_val.setStyleSheet("color: #3b82f6;") # blue
        elif health >= 50:
            self.hc_val.setText(f"{health}% — Moderate")
            self.hc_val.setStyleSheet("color: #f59e0b;") # amber yellow
        else:
            self.hc_val.setText(f"{health}% — Clean Required")
            self.hc_val.setStyleSheet("color: #ef4444;") # red

        # 2. Update Charts
        self.donut_chart.set_data(donut_data)

        # 3. Update Largest Files
        self.largest_list.clear()
        largest_files = db.get_largest_files(15)
        for idx, file_rec in enumerate(largest_files):
            size_str = format_size(file_rec["size"])
            item_text = f" {idx+1}. {file_rec['name']} ({size_str}) — {file_rec['path']}"
            item = QListWidgetItem(item_text)
            self.largest_list.addItem(item)

        # 4. Rebuild Treemap Tree (only if we have a scanned path)
        if self.last_scanned_dir and os.path.exists(self.last_scanned_dir):
            try:
                tree_root = build_tree_from_db(self.last_scanned_dir)
                self.treemap.set_data(tree_root)
            except Exception as e:
                print(f"Error building treemap: {e}")
