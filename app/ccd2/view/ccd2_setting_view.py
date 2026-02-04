"""
CCD2 Setting View - Giao diện cấu hình cho CCD2
Chức năng:
- Hiển thị camera CCD2 toàn màn hình
- Template check mã datamatrix như cũ
- Quản lý template và regions
"""
import logging
import numpy as np
import cv2
from typing import Optional, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QTextEdit, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QSlider, QCheckBox, QComboBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
import sys
import os

# Import shared widget
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app.shared.view.image_display_widget import ImageDisplayWidget

logger = logging.getLogger(__name__)


class CCD2SettingView(QMainWindow):
    """
    Giao diện setting riêng cho CCD2
    - Hiển thị camera CCD2 toàn màn hình
    - Template check mã datamatrix
    - Nút Save/Cancel để quay về main view
    """
    
    # Signals
    save_requested = Signal()
    cancel_requested = Signal()
    roi_selected = Signal(int, int, int, int)  # x, y, width, height
    template_selected = Signal(str)  # template name
    region_add_requested = Signal()
    region_edit_requested = Signal(int)  # region index
    region_delete_requested = Signal(int)  # region index
    process_test_requested = Signal()
    capture_master_requested = Signal()  # Capture master image from stream
    save_new_template_requested = Signal(str, str)  # name, description
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        logger.info("CCD2SettingView initialized")
    
    def _init_ui(self):
        """Khởi tạo giao diện CCD2 Setting"""
        self.setWindowTitle("CCD2 - Setting (Datamatrix Scanning)")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Camera display (lớn)
        left_panel = self._create_camera_panel()
        main_layout.addWidget(left_panel, stretch=3)
        
        # Right panel - Controls
        right_panel = self._create_control_panel()
        main_layout.addWidget(right_panel, stretch=1)
    
    def _create_camera_panel(self) -> QWidget:
        """Tạo panel hiển thị camera CCD2"""
        container = QWidget()
        layout = QVBoxLayout()
        
        # Group: CCD2 Camera View
        group_camera = QGroupBox("CCD2 - Camera View")
        layout_camera = QVBoxLayout()
        
        # Image display với ROI selection
        self.image_display = ImageDisplayWidget()
        self.image_display.setMinimumSize(800, 600)
        self.image_display.roi_selected.connect(self._on_roi_selected)
        layout_camera.addWidget(self.image_display)
        
        # Info label
        self.info_label = QLabel("CCD2: Ready for template configuration")
        self.info_label.setStyleSheet("color: #00AA00; padding: 5px; font-weight: bold;")
        layout_camera.addWidget(self.info_label)
        
        group_camera.setLayout(layout_camera)
        layout.addWidget(group_camera)
        
        container.setLayout(layout)
        return container
    
    def _create_control_panel(self) -> QWidget:
        """Tạo panel điều khiển"""
        container = QWidget()
        layout = QVBoxLayout()
        
        # === Template Selection ===
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout()
        
        template_layout.addWidget(QLabel("Select Template:"))
        self.combo_template = QComboBox()
        self.combo_template.addItem("-- No Template --")
        self.combo_template.currentTextChanged.connect(self._on_template_changed)
        template_layout.addWidget(self.combo_template)
        
        self.lbl_template_info = QLabel("No template loaded")
        self.lbl_template_info.setStyleSheet("color: #888; font-size: 10px;")
        self.lbl_template_info.setWordWrap(True)
        template_layout.addWidget(self.lbl_template_info)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # === Region Management ===
        region_group = QGroupBox("Regions")
        region_layout = QVBoxLayout()
        
        btn_row = QHBoxLayout()
        self.btn_region_add = QPushButton("Add")
        self.btn_region_add.clicked.connect(self._on_region_add_clicked)
        btn_row.addWidget(self.btn_region_add)
        
        self.btn_region_edit = QPushButton("Edit")
        self.btn_region_edit.clicked.connect(self._on_region_edit_clicked)
        self.btn_region_edit.setEnabled(False)
        btn_row.addWidget(self.btn_region_edit)
        
        self.btn_region_delete = QPushButton("Delete")
        self.btn_region_delete.clicked.connect(self._on_region_delete_clicked)
        self.btn_region_delete.setEnabled(False)
        btn_row.addWidget(self.btn_region_delete)
        
        region_layout.addLayout(btn_row)
        
        # Regions table
        self.table_regions = QTableWidget(0, 6)
        self.table_regions.setHorizontalHeaderLabels(
            ["Name", "X", "Y", "W", "H", "Barcode"]
        )
        self.table_regions.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_regions.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_regions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_regions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_regions.itemSelectionChanged.connect(self._on_region_selection_changed)
        region_layout.addWidget(self.table_regions)
        
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        # === Template Creation (NEW) ===
        creation_group = QGroupBox("Create New Template")
        creation_layout = QVBoxLayout()
        
        # Template name and description
        creation_layout.addWidget(QLabel("Template Name:"))
        self.txt_new_template_name = QLineEdit()
        self.txt_new_template_name.setPlaceholderText("Enter template name...")
        creation_layout.addWidget(self.txt_new_template_name)
        
        creation_layout.addWidget(QLabel("Description:"))
        self.txt_new_template_desc = QLineEdit()
        self.txt_new_template_desc.setPlaceholderText("Enter description...")
        creation_layout.addWidget(self.txt_new_template_desc)
        
        # Capture master image button
        self.btn_capture_master = QPushButton("Capture Master Image from Stream")
        self.btn_capture_master.clicked.connect(self._on_capture_master_clicked)
        creation_layout.addWidget(self.btn_capture_master)
        
        self.lbl_master_status = QLabel("No master image captured")
        self.lbl_master_status.setStyleSheet("color: #888; font-size: 10px;")
        creation_layout.addWidget(self.lbl_master_status)
        
        # Save new template button
        self.btn_save_new_template = QPushButton("Save New Template")
        self.btn_save_new_template.clicked.connect(self._on_save_new_template_clicked)
        self.btn_save_new_template.setEnabled(False)
        creation_layout.addWidget(self.btn_save_new_template)
        
        creation_group.setLayout(creation_layout)
        layout.addWidget(creation_group)
        
        # === Test Processing ===
        test_group = QGroupBox("Test Processing")
        test_layout = QVBoxLayout()
        
        self.btn_process_test = QPushButton("Process Current Frame")
        self.btn_process_test.clicked.connect(self._on_process_test_clicked)
        test_layout.addWidget(self.btn_process_test)
        
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setMaximumHeight(120)
        self.txt_results.setPlaceholderText("Test results will appear here...")
        test_layout.addWidget(self.txt_results)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # === Save/Cancel Buttons ===
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        container.setLayout(layout)
        return container
    
    def _on_roi_selected(self, x: int, y: int, width: int, height: int):
        """Handle ROI selection"""
        self.roi_selected.emit(x, y, width, height)
        logger.info(f"ROI selected: ({x}, {y}, {width}x{height})")
    
    def _on_template_changed(self, template_name: str):
        """Handle template selection change"""
        if template_name and template_name != "-- No Template --":
            self.template_selected.emit(template_name)
    
    def _on_region_add_clicked(self):
        """Handle add region button"""
        self.region_add_requested.emit()
    
    def _on_region_edit_clicked(self):
        """Handle edit region button"""
        selected_rows = self.table_regions.selectedItems()
        if selected_rows:
            row = self.table_regions.currentRow()
            self.region_edit_requested.emit(row)
    
    def _on_region_delete_clicked(self):
        """Handle delete region button"""
        selected_rows = self.table_regions.selectedItems()
        if selected_rows:
            row = self.table_regions.currentRow()
            self.region_delete_requested.emit(row)
    
    def _on_region_selection_changed(self):
        """Handle region selection change"""
        has_selection = len(self.table_regions.selectedItems()) > 0
        self.btn_region_edit.setEnabled(has_selection)
        self.btn_region_delete.setEnabled(has_selection)
    
    def _on_process_test_clicked(self):
        """Handle process test button"""
        self.process_test_requested.emit()
    
    def _on_capture_master_clicked(self):
        """Handle capture master image button"""
        self.capture_master_requested.emit()
    
    def _on_save_new_template_clicked(self):
        """Handle save new template button"""
        name = self.txt_new_template_name.text().strip()
        desc = self.txt_new_template_desc.text().strip()
        
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input", "Please enter a template name")
            return
        
        self.save_new_template_requested.emit(name, desc)
    
    def _on_save_clicked(self):
        """Handle save button"""
        self.save_requested.emit()
    
    def _on_cancel_clicked(self):
        """Handle cancel button"""
        self.cancel_requested.emit()
    
    def display_image(self, frame: np.ndarray):
        """Hiển thị ảnh từ CCD2"""
        try:
            # Convert BGR to RGB if needed
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage
            if len(frame.shape) == 2:  # Grayscale
                height, width = frame.shape
                bytes_per_line = width
                q_image = QImage(
                    frame.data, width, height, bytes_per_line,
                    QImage.Format_Grayscale8
                )
            else:  # Color
                height, width, channels = frame.shape
                bytes_per_line = channels * width
                q_image = QImage(
                    frame.data, width, height, bytes_per_line,
                    QImage.Format_RGB888
                )
            
            pixmap = QPixmap.fromImage(q_image)
            self.image_display.set_image(pixmap)
        except Exception as e:
            logger.error(f"Failed to display CCD2 image: {e}", exc_info=True)
    
    def update_template_list(self, templates: List[str]):
        """Cập nhật danh sách template"""
        current = self.combo_template.currentText()
        self.combo_template.clear()
        self.combo_template.addItem("-- No Template --")
        for template in templates:
            self.combo_template.addItem(template)
        
        # Restore selection if possible
        if current in templates:
            self.combo_template.setCurrentText(current)
    
    def update_template_info(self, info: str):
        """Cập nhật thông tin template"""
        self.lbl_template_info.setText(info)
        if info != "No template loaded":
            self.lbl_template_info.setStyleSheet("color: #00AA00; font-size: 10px;")
        else:
            self.lbl_template_info.setStyleSheet("color: #888; font-size: 10px;")
    
    def update_regions_table(self, regions: list):
        """Cập nhật bảng regions"""
        self.table_regions.setRowCount(0)
        
        for region in regions:
            row = self.table_regions.rowCount()
            self.table_regions.insertRow(row)
            
            self.table_regions.setItem(row, 0, QTableWidgetItem(region.name))
            self.table_regions.setItem(row, 1, QTableWidgetItem(str(region.x)))
            self.table_regions.setItem(row, 2, QTableWidgetItem(str(region.y)))
            self.table_regions.setItem(row, 3, QTableWidgetItem(str(region.width)))
            self.table_regions.setItem(row, 4, QTableWidgetItem(str(region.height)))
            self.table_regions.setItem(row, 5, QTableWidgetItem("Yes" if region.scan_barcode else "No"))
    
    def update_results(self, results: str):
        """Cập nhật kết quả test"""
        self.txt_results.setText(results)
    
    def update_master_status(self, status: str, enable_save: bool = False):
        """Cập nhật trạng thái master image"""
        self.lbl_master_status.setText(status)
        if "captured" in status.lower():
            self.lbl_master_status.setStyleSheet("color: #00AA00; font-size: 10px;")
        else:
            self.lbl_master_status.setStyleSheet("color: #888; font-size: 10px;")
        
        self.btn_save_new_template.setEnabled(enable_save)

