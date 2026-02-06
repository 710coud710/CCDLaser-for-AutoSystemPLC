"""
CCD1 Setting View - Giao diện cấu hình cho CCD1
Chức năng:
- Hiển thị camera CCD1 toàn màn hình
- Tạo vùng ROI để so sánh với mẫu (template matching)
- Nếu giống mẫu ở tọa độ đó thì OK, không thì ERROR
"""
import logging
import numpy as np
import cv2
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QTextEdit, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QSlider, QCheckBox, QTabWidget, QLineEdit,
    QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
import sys
import os

# Import shared widget
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app.shared.view.image_display_widget import ImageDisplayWidget

logger = logging.getLogger(__name__)


class CCD1SettingView(QMainWindow):
    """
    Giao diện setting riêng cho CCD1
    - Hiển thị camera CCD1 toàn màn hình
    - Tạo ROI và so sánh với template
    - Nút Save/Cancel để quay về main view
    """
    
    # Signals
    save_requested = Signal()
    cancel_requested = Signal()
    roi_selected = Signal(int, int, int, int)  # x, y, width, height
    template_selected = Signal(str)
    set_pattern_requested = Signal() # Set current ROI as pattern for selected template
    template_load_requested = Signal()
    template_capture_requested = Signal()  # Capture from stream
    threshold_changed = Signal(float)
    save_template_requested = Signal(str)  # title
    exposure_changed = Signal(int)
    gain_changed = Signal(int)
    brightness_changed = Signal(int)
    contrast_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        logger.info("CCD1SettingView initialized")
    
    def _init_ui(self):
        """Khởi tạo giao diện CCD1 Setting"""
        self.setWindowTitle("CCD1 - Setting (ROI Template Matching)")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Camera display (lớn)
        left_panel = self._create_camera_panel()
        main_layout.addWidget(left_panel, stretch=3)
        
        # Right panel - Tab widget cho Template và Setting
        right_tabs = QTabWidget()
        
        # Template tab
        template_panel = self._create_template_panel()
        right_tabs.addTab(template_panel, "Template")
        
        # Setting tab (camera parameters)
        setting_panel = self._create_setting_panel()
        right_tabs.addTab(setting_panel, "Setting")
        
        main_layout.addWidget(right_tabs, stretch=1)
    
    def _create_camera_panel(self) -> QWidget:
        """Tạo panel hiển thị camera CCD1"""
        container = QWidget()
        layout = QVBoxLayout()
        
        # Group: CCD1 Camera View
        group_camera = QGroupBox("CCD1 - Camera View")
        layout_camera = QVBoxLayout()
        
        # Image display với ROI selection
        self.image_display = ImageDisplayWidget()
        self.image_display.setMinimumSize(800, 600)
        self.image_display.roi_selected.connect(self._on_roi_selected)
        layout_camera.addWidget(self.image_display)
        
        # Info label
        self.info_label = QLabel("CCD1: Ready for ROI selection")
        self.info_label.setStyleSheet("color: #00AA00; padding: 5px; font-weight: bold;")
        layout_camera.addWidget(self.info_label)
        
        group_camera.setLayout(layout_camera)
        layout.addWidget(group_camera)
        
        container.setLayout(layout)
        return container
    
    def _create_template_panel(self) -> QWidget:
        """Tạo panel Template (ROI và Template Matching)"""
        container = QWidget()
        layout = QVBoxLayout()
        
        # === ROI Selection ===
        roi_group = QGroupBox("ROI Selection")
        roi_layout = QVBoxLayout()
        
        roi_layout.addWidget(QLabel("1. Click and drag on image to select ROI"))
        
        # ROI info
        roi_info_layout = QHBoxLayout()
        roi_info_layout.addWidget(QLabel("ROI:"))
        self.lbl_roi_info = QLabel("Not selected")
        self.lbl_roi_info.setStyleSheet("color: #888;")
        roi_info_layout.addWidget(self.lbl_roi_info)
        roi_layout.addLayout(roi_info_layout)
        
        roi_group.setLayout(roi_layout)
        layout.addWidget(roi_group)
        
        # === Template Selection ===
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout()
        
        template_layout.addWidget(QLabel("Select Template:"))
        self.combo_template = QComboBox()
        self.combo_template.addItem("-- No Template --")
        self.combo_template.currentTextChanged.connect(self._on_template_changed)
        template_layout.addWidget(self.combo_template)
        
        # Pattern Settings
        template_layout.addWidget(QLabel("Pattern Settings:"))
        
        self.btn_set_pattern = QPushButton("Set Pattern from ROI")
        self.btn_set_pattern.setToolTip("Capture current ROI and save as pattern for this template")
        self.btn_set_pattern.clicked.connect(self._on_set_pattern_clicked)
        self.btn_set_pattern.setEnabled(False) 
        template_layout.addWidget(self.btn_set_pattern)
        
        self.lbl_pattern_info = QLabel("No pattern set")
        self.lbl_pattern_info.setStyleSheet("color: #888; font-size: 10px;")
        self.lbl_pattern_info.setWordWrap(True)
        template_layout.addWidget(self.lbl_pattern_info)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # === Matching Parameters ===
        params_group = QGroupBox("Matching Parameters")
        params_layout = QVBoxLayout()
        
        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Match Threshold:"))
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.0, 1.0)
        self.spin_threshold.setSingleStep(0.01)
        self.spin_threshold.setValue(0.8)
        self.spin_threshold.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self.spin_threshold)
        params_layout.addLayout(threshold_layout)
        
        # Show ROI checkbox
        self.chk_show_roi = QCheckBox("Show ROI on image")
        self.chk_show_roi.setChecked(True)
        params_layout.addWidget(self.chk_show_roi)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # === Matching Results ===
        results_group = QGroupBox("Matching Results")
        results_layout = QVBoxLayout()
        
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setMaximumHeight(150)
        self.txt_results.setPlaceholderText("Matching results will appear here...")
        results_layout.addWidget(self.txt_results)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        container.setLayout(layout)
        return container
    
    def _create_setting_panel(self) -> QWidget:
        """Tạo panel Setting (Camera Parameters)"""
        container = QWidget()
        layout = QVBoxLayout()
        
        # === Camera Parameters ===
        camera_params_group = QGroupBox("Camera Parameters")
        camera_params_layout = QVBoxLayout()
        
        # Exposure Time
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("Exposure (μs):"))
        self.spin_exposure = QSpinBox()
        self.spin_exposure.setRange(1, 1000000)
        self.spin_exposure.setValue(10000)
        self.spin_exposure.setSuffix(" μs")
        self.spin_exposure.valueChanged.connect(self._on_exposure_changed)
        exposure_layout.addWidget(self.spin_exposure)
        camera_params_layout.addLayout(exposure_layout)
        
        # Gain
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain (dB):"))
        self.spin_gain = QSpinBox()
        self.spin_gain.setRange(0, 100)
        self.spin_gain.setValue(0)
        self.spin_gain.setSuffix(" dB")
        self.spin_gain.valueChanged.connect(self._on_gain_changed)
        gain_layout.addWidget(self.spin_gain)
        camera_params_layout.addLayout(gain_layout)
        
        # Brightness
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Brightness:"))
        self.slider_brightness = QSlider(Qt.Horizontal)
        self.slider_brightness.setRange(1, 100)
        self.slider_brightness.setValue(50)
        self.slider_brightness.valueChanged.connect(self._on_brightness_changed)
        brightness_layout.addWidget(self.slider_brightness)
        self.lbl_brightness_value = QLabel("50")
        self.lbl_brightness_value.setMinimumWidth(30)
        brightness_layout.addWidget(self.lbl_brightness_value)
        camera_params_layout.addLayout(brightness_layout)
        
        # Contrast
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Contrast:"))
        self.slider_contrast = QSlider(Qt.Horizontal)
        self.slider_contrast.setRange(-100, 100)
        self.slider_contrast.setValue(0)
        self.slider_contrast.valueChanged.connect(self._on_contrast_changed)
        contrast_layout.addWidget(self.slider_contrast)
        self.lbl_contrast_value = QLabel("0")
        self.lbl_contrast_value.setMinimumWidth(30)
        contrast_layout.addWidget(self.lbl_contrast_value)
        camera_params_layout.addLayout(contrast_layout)
        
        camera_params_group.setLayout(camera_params_layout)
        layout.addWidget(camera_params_group)
        
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
        self.lbl_roi_info.setText(f"({x}, {y}, {width}x{height})")
        self.lbl_roi_info.setStyleSheet("color: #00AA00;")
        self.roi_selected.emit(x, y, width, height)
        logger.info(f"ROI selected: ({x}, {y}, {width}x{height})")
    

    
    def _on_template_changed(self, template_name: str):
        """Handle template selection change"""
        if template_name and template_name != "-- No Template --":
            self.template_selected.emit(template_name)
            self.btn_set_pattern.setEnabled(True)
        else:
            self.btn_set_pattern.setEnabled(False)
            self.update_pattern_info("No template selected")
            
    def _on_set_pattern_clicked(self):
        """Handle set pattern button"""
        self.set_pattern_requested.emit()

    def update_template_list(self, templates: list):
        current = self.combo_template.currentText()
        self.combo_template.blockSignals(True)
        self.combo_template.clear()
        self.combo_template.addItem("-- No Template --")
        for t in templates:
            self.combo_template.addItem(t)
        
        if current in templates:
            self.combo_template.setCurrentText(current)
        self.combo_template.blockSignals(False)

    def update_pattern_info(self, info: str):
        self.lbl_pattern_info.setText(info)
        if "set" in info.lower() or "loaded" in info.lower() or "saved" in info.lower():
            self.lbl_pattern_info.setStyleSheet("color: #00AA00; font-size: 10px;")
        else:
            self.lbl_pattern_info.setStyleSheet("color: #888; font-size: 10px;")
    
    def _on_threshold_changed(self, value: float):
        """Handle threshold change"""
        self.threshold_changed.emit(value)
    
    def _on_exposure_changed(self, value: int):
        """Handle exposure change"""
        self.exposure_changed.emit(value)
    
    def _on_gain_changed(self, value: int):
        """Handle gain change"""
        self.gain_changed.emit(value)
    
    def _on_brightness_changed(self, value: int):
        """Handle brightness change"""
        self.lbl_brightness_value.setText(str(value))
        self.brightness_changed.emit(value)
    
    def _on_contrast_changed(self, value: int):
        """Handle contrast change"""
        self.lbl_contrast_value.setText(str(value))
        self.contrast_changed.emit(value)
    
    def _on_save_clicked(self):
        """Handle save button"""
        self.save_requested.emit()
    
    def _on_cancel_clicked(self):
        """Handle cancel button"""
        self.cancel_requested.emit()
    
    def display_image(self, frame: np.ndarray):
        """Hiển thị ảnh từ CCD1"""
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
            logger.error(f"Failed to display CCD1 image: {e}", exc_info=True)
    

    
    def update_results(self, results: str):
        """Cập nhật kết quả matching"""
        self.txt_results.setText(results)
    
    def get_threshold(self) -> float:
        """Lấy giá trị threshold"""
        return self.spin_threshold.value()
    
    def get_show_roi(self) -> bool:
        """Lấy trạng thái show ROI"""
        return self.chk_show_roi.isChecked()
