"""
Main View - Giao diện chính của ứng dụng
Sử dụng PySide6 (Qt)
"""
import logging
from typing import Optional
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox, QStatusBar,
    QSlider, QSpinBox, QCheckBox, QTextEdit, QComboBox,
    QLineEdit, QTabWidget, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QIcon
from .view_interface import IView, IPresenter
from .image_display_widget import ImageDisplayWidget

logger = logging.getLogger(__name__)


class MainView(QMainWindow):
    """
    Main Window của ứng dụng
    Hiển thị:
    - Video stream từ camera
    - Các nút điều khiển
    - Thông tin trạng thái
    """
    
    def __init__(self):
        super().__init__()
        self._presenter: Optional[IPresenter] = None
        
        # ROI selection state
        self._roi_selection_mode = None  # None, 'template', or 'qr_roi'
        self._last_captured_image: Optional[np.ndarray] = None
        
        self._init_ui()
        logger.info("MainView initialized")
    
    def set_presenter(self, presenter: IPresenter):
        """Set presenter cho view"""
        self._presenter = presenter
        logger.info("Presenter attached to view")
    
    def _init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("CCDLaser - Camera Control")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Camera display
        left_panel = self._create_camera_panel()
        main_layout.addWidget(left_panel, stretch=3)
        
        # Right panel - Controls (with tabs for Teaching/Running)
        right_panel = self._create_control_panel_with_tabs()
        main_layout.addWidget(right_panel, stretch=1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        logger.info("UI initialized")
    
    def _create_camera_panel(self) -> QWidget:
        """Tạo panel hiển thị camera"""
        group = QGroupBox("Camera View")
        layout = QVBoxLayout()
        
        # Custom image display widget with ROI selection
        self.image_display = ImageDisplayWidget()
        self.image_display.roi_selected.connect(self._on_roi_selected)
        layout.addWidget(self.image_display)
        

        self.info_label = QLabel("Camera: Not connected")
        self.info_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.info_label)
        group.setLayout(layout)
        return group
    
    def _create_control_panel_with_tabs(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        conn_group = self._create_connection_group()
        layout.addWidget(conn_group)
        
        # Streaming group (chung cho cả 2 mode)
        stream_group = self._create_streaming_group()
        layout.addWidget(stream_group)
        
        # Tab widget cho Running/Template mode
        self.mode_tabs = QTabWidget()
        
        # Running Mode tab (dùng template đã chọn)
        running_tab = self._create_running_mode_panel()
        self.mode_tabs.addTab(running_tab, "Running Mode")
        
        # Template Mode tab (chỉnh sửa template)
        template_tab = self._create_template_mode_panel()
        self.mode_tabs.addTab(template_tab, "Template Mode")
        
        # Setting tab (camera parameters)
        setting_tab = self._create_setting_mode_panel()
        self.mode_tabs.addTab(setting_tab, "Setting")
        
        layout.addWidget(self.mode_tabs)
        
        # Camera info (chung) - hiển thị ở dưới cùng
        info_group = self._create_camera_info_group()
        layout.addWidget(info_group)
        
        # Spacer
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _create_connection_group(self) -> QGroupBox:
        """Tạo connection group - chỉ hiển thị 1 nút tại một thời điểm"""
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        
        # Tạo cả 2 nút nhưng chỉ hiển thị 1 cái
        self.btn_connect = QPushButton("Connect Camera")
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        conn_layout.addWidget(self.btn_connect)
        
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)
        self.btn_disconnect.setVisible(False)  # Ẩn ban đầu
        conn_layout.addWidget(self.btn_disconnect)
        
        conn_group.setLayout(conn_layout)
        return conn_group
    
    def _create_streaming_group(self) -> QGroupBox:
        """Tạo streaming group với icon và xếp ngang"""
        stream_group = QGroupBox("Streaming")
        stream_layout = QHBoxLayout()  # Xếp ngang
        stream_layout.setSpacing(5)  # Khoảng cách giữa các nút
        
        # Helper function để tạo icon với fallback
        def get_icon(theme_names, fallback_text):
            """Lấy icon từ theme hoặc tạo icon từ text"""
            for theme_name in theme_names:
                icon = QIcon.fromTheme(theme_name)
                if not icon.isNull():
                    return icon
            # Fallback: Tạo icon từ text symbol (Unicode)
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(QColor(50, 50, 50))  # Màu xám đậm
            font = painter.font()
            font.setPixelSize(22)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, fallback_text)
            painter.end()
            return QIcon(pixmap)
        
        # Start Stream button với icon
        self.btn_start_stream = QPushButton()
        start_icon = get_icon(["media-playback-start", "media-play", "play"], "▶")
        self.btn_start_stream.setIcon(start_icon)
        self.btn_start_stream.setToolTip("Start Stream")
        self.btn_start_stream.clicked.connect(self._on_start_stream_clicked)
        self.btn_start_stream.setEnabled(False)
        self.btn_start_stream.setMinimumSize(40, 40)  # Kích thước icon button
        stream_layout.addWidget(self.btn_start_stream)
        
        # Stop Stream button với icon
        self.btn_stop_stream = QPushButton()
        stop_icon = get_icon(["media-playback-stop", "media-stop", "stop"], "■")
        self.btn_stop_stream.setIcon(stop_icon)
        self.btn_stop_stream.setToolTip("Stop Stream")
        self.btn_stop_stream.clicked.connect(self._on_stop_stream_clicked)
        self.btn_stop_stream.setEnabled(False)
        self.btn_stop_stream.setVisible(False)  # Ẩn ban đầu, chỉ hiện khi streaming
        self.btn_stop_stream.setMinimumSize(40, 40)
        stream_layout.addWidget(self.btn_stop_stream)
        
        # Capture Image button với icon
        self.btn_capture = QPushButton()
        capture_icon = get_icon(["camera-photo", "camera", "camera-web"], "●")
        self.btn_capture.setIcon(capture_icon)
        self.btn_capture.setToolTip("Capture Image")
        self.btn_capture.clicked.connect(self._on_capture_clicked)
        self.btn_capture.setEnabled(False)
        self.btn_capture.setMinimumSize(40, 40)
        stream_layout.addWidget(self.btn_capture)
        
        # Thêm stretch để căn trái
        stream_layout.addStretch()
        
        stream_group.setLayout(stream_layout)
        return stream_group
    
    
    def _create_template_mode_panel(self) -> QWidget:
        """Tạo panel cho Template Mode - Simple template system"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # === TEMPLATE CREATION SECTION ===
        creation_group = QGroupBox("Create New Template")
        creation_layout = QVBoxLayout()
        
        # Load master image
        creation_layout.addWidget(QLabel("1. Load Master Image:"))
        self.btn_template_load_image = QPushButton("Load Image from File/Camera")
        self.btn_template_load_image.clicked.connect(self._on_template_load_image_clicked)
        creation_layout.addWidget(self.btn_template_load_image)
        
        self.lbl_template_image_source = QLabel("No image loaded")
        self.lbl_template_image_source.setStyleSheet("color: #888; font-size: 10px;")
        creation_layout.addWidget(self.lbl_template_image_source)
        
        # Template info
        creation_layout.addWidget(QLabel("2. Template Info:"))
        self.txt_template_name = QLineEdit()
        self.txt_template_name.setPlaceholderText("Enter template name...")
        creation_layout.addWidget(self.txt_template_name)
        
        self.txt_template_desc = QLineEdit()
        self.txt_template_desc.setPlaceholderText("Enter description...")
        creation_layout.addWidget(self.txt_template_desc)
        
        # Add regions
        creation_layout.addWidget(QLabel("3. Define Regions (Crop + Barcode):"))
        
        btn_layout = QHBoxLayout()
        self.btn_add_crop_region = QPushButton("Add Region")
        self.btn_add_crop_region.clicked.connect(self._on_add_crop_region_clicked)
        self.btn_add_crop_region.setEnabled(False)
        btn_layout.addWidget(self.btn_add_crop_region)
        
        # Checkbox để chọn có scan barcode không (mặc định có)
        self.chk_scan_barcode = QCheckBox("Scan Barcode in Region")
        self.chk_scan_barcode.setChecked(True)  # Mặc định scan barcode
        btn_layout.addWidget(self.chk_scan_barcode)
        creation_layout.addLayout(btn_layout)
        
        # Regions list
        self.txt_template_regions_list = QTextEdit()
        self.txt_template_regions_list.setReadOnly(True)
        self.txt_template_regions_list.setMaximumHeight(120)
        self.txt_template_regions_list.setPlaceholderText("No regions defined")
        creation_layout.addWidget(self.txt_template_regions_list)
        
        # Save template
        self.btn_save_template = QPushButton("Save Template")
        self.btn_save_template.clicked.connect(self._on_save_template_clicked)
        self.btn_save_template.setEnabled(False)
        creation_layout.addWidget(self.btn_save_template)
        
        creation_group.setLayout(creation_layout)
        layout.addWidget(creation_group)
        
        # === TEMPLATE PROCESSING SECTION ===
        processing_group = QGroupBox("Process with Template")
        processing_layout = QVBoxLayout()
        
        # Template selection
        processing_layout.addWidget(QLabel("Select Template:"))
        self.combo_template = QComboBox()
        self.combo_template.addItem("-- No Template --")
        processing_layout.addWidget(self.combo_template)
        
        btn_layout2 = QHBoxLayout()
        self.btn_load_template = QPushButton("Load Template")
        self.btn_load_template.clicked.connect(self._on_load_template_clicked)
        btn_layout2.addWidget(self.btn_load_template)
        
        self.btn_refresh_templates = QPushButton("Refresh")
        self.btn_refresh_templates.clicked.connect(self._on_refresh_templates_clicked)
        btn_layout2.addWidget(self.btn_refresh_templates)
        processing_layout.addLayout(btn_layout2)
        
        # Current template info
        self.lbl_current_template_info = QLabel("No template loaded")
        self.lbl_current_template_info.setStyleSheet("color: #888;")
        self.lbl_current_template_info.setWordWrap(True)
        processing_layout.addWidget(self.lbl_current_template_info)
        
        # Load test image
        processing_layout.addWidget(QLabel("Load Image to Process:"))
        self.btn_template_load_test_image = QPushButton("Load Test Image")
        self.btn_template_load_test_image.clicked.connect(self._on_template_load_test_image_clicked)
        processing_layout.addWidget(self.btn_template_load_test_image)
        
        self.lbl_template_test_image = QLabel("No test image")
        self.lbl_template_test_image.setStyleSheet("color: #888; font-size: 10px;")
        processing_layout.addWidget(self.lbl_template_test_image)
        
        # Process button
        self.btn_process_template = QPushButton("Process Image")
        self.btn_process_template.clicked.connect(self._on_process_template_clicked)
        self.btn_process_template.setEnabled(False)
        processing_layout.addWidget(self.btn_process_template)
        
        # Results
        processing_layout.addWidget(QLabel("Results:"))
        self.txt_template_results = QTextEdit()
        self.txt_template_results.setReadOnly(True)
        self.txt_template_results.setMaximumHeight(100)
        self.txt_template_results.setPlaceholderText("No results yet")
        processing_layout.addWidget(self.txt_template_results)
        
        # Visualization options
        vis_layout = QHBoxLayout()
        self.chk_show_regions = QCheckBox("Show Regions")
        self.chk_show_regions.setChecked(True)
        vis_layout.addWidget(self.chk_show_regions)
        processing_layout.addLayout(vis_layout)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_running_mode_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Template selection
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout()
        
        template_layout.addWidget(QLabel("Select Template:"))
        self.combo_running_template = QComboBox()
        self.combo_running_template.addItem("-- No Template --")
        template_layout.addWidget(self.combo_running_template)
        
        self.btn_load_running_template = QPushButton("Load Template")
        self.btn_load_running_template.clicked.connect(self._on_load_running_template_clicked)
        template_layout.addWidget(self.btn_load_running_template)
        
        self.btn_refresh_running_templates = QPushButton("Refresh List")
        self.btn_refresh_running_templates.clicked.connect(self._on_refresh_running_templates_clicked)
        template_layout.addWidget(self.btn_refresh_running_templates)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Test Image Source (for testing without camera)
        test_group = QGroupBox("Test Image Source")
        test_layout = QVBoxLayout()
        
        self.btn_load_test_image = QPushButton("Load Image for Testing")
        self.btn_load_test_image.clicked.connect(self._on_load_test_image_clicked)
        test_layout.addWidget(self.btn_load_test_image)
        
        self.lbl_test_image_source = QLabel("No test image loaded")
        self.lbl_test_image_source.setStyleSheet("color: #888; font-size: 10px;")
        self.lbl_test_image_source.setWordWrap(True)
        test_layout.addWidget(self.lbl_test_image_source)
        
        self.btn_process_test_image = QPushButton("Process Test Image")
        self.btn_process_test_image.clicked.connect(self._on_process_test_image_clicked)
        self.btn_process_test_image.setEnabled(False)
        test_layout.addWidget(self.btn_process_test_image)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Template info display
        info_group = QGroupBox("Current Template")
        info_layout = QVBoxLayout()
        
        self.lbl_current_template = QLabel("No template loaded")
        self.lbl_current_template.setStyleSheet("color: #888;")
        self.lbl_current_template.setWordWrap(True)
        info_layout.addWidget(self.lbl_current_template)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Barcode Detection control
        barcode_group = QGroupBox("Barcode Detection")
        barcode_layout = QVBoxLayout()
        
        self.chk_barcode_enabled = QCheckBox("Enable Barcode Detection")
        self.chk_barcode_enabled.setChecked(True)
        self.chk_barcode_enabled.stateChanged.connect(self._on_barcode_enabled_changed)
        barcode_layout.addWidget(self.chk_barcode_enabled)
        
        self.chk_show_regions = QCheckBox("Show Regions")
        self.chk_show_regions.setChecked(True)
        barcode_layout.addWidget(self.chk_show_regions)
        
        barcode_group.setLayout(barcode_layout)
        layout.addWidget(barcode_group)
        
        # Barcode Results display
        results_group = QGroupBox("Barcode Results")
        results_layout = QVBoxLayout()
        
        self.txt_barcode_results = QTextEdit()
        self.txt_barcode_results.setReadOnly(True)
        self.txt_barcode_results.setMaximumHeight(150)
        self.txt_barcode_results.setPlaceholderText("No barcodes detected")
        results_layout.addWidget(self.txt_barcode_results)
        
        self.btn_clear_barcode = QPushButton("Clear Results")
        self.btn_clear_barcode.clicked.connect(self._on_clear_barcode_clicked)
        results_layout.addWidget(self.btn_clear_barcode)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_setting_mode_panel(self) -> QWidget:
        """Tạo panel cho Setting Mode - điều chỉnh camera parameters"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Camera Parameters Group
        params_group = QGroupBox("Camera Parameters")
        params_layout = QVBoxLayout()
        
        # Exposure Time
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("Exposure Time (μs):"))
        self.spin_exposure = QSpinBox()
        self.spin_exposure.setRange(1, 1000000)
        self.spin_exposure.setValue(10000)
        self.spin_exposure.setSuffix(" μs")
        self.spin_exposure.valueChanged.connect(self._on_exposure_changed)
        exposure_layout.addWidget(self.spin_exposure)
        params_layout.addLayout(exposure_layout)
        
        # Gain
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain (dB):"))
        self.spin_gain_setting = QSpinBox()
        self.spin_gain_setting.setRange(0, 100)
        self.spin_gain_setting.setValue(0)
        self.spin_gain_setting.setSuffix(" dB")
        self.spin_gain_setting.valueChanged.connect(self._on_gain_setting_changed)
        gain_layout.addWidget(self.spin_gain_setting)
        params_layout.addLayout(gain_layout)
        
        # Brightness (Gamma)
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Brightness (Gamma):"))
        self.slider_brightness = QSlider(Qt.Horizontal)
        self.slider_brightness.setRange(1, 100)
        self.slider_brightness.setValue(50)
        self.slider_brightness.valueChanged.connect(self._on_brightness_changed)
        brightness_layout.addWidget(self.slider_brightness)
        self.lbl_brightness_value = QLabel("50")
        self.lbl_brightness_value.setMinimumWidth(30)
        brightness_layout.addWidget(self.lbl_brightness_value)
        params_layout.addLayout(brightness_layout)
        
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
        params_layout.addLayout(contrast_layout)
        
        # Saturation (for color cameras)
        saturation_layout = QHBoxLayout()
        saturation_layout.addWidget(QLabel("Saturation:"))
        self.slider_saturation = QSlider(Qt.Horizontal)
        self.slider_saturation.setRange(0, 100)
        self.slider_saturation.setValue(50)
        self.slider_saturation.valueChanged.connect(self._on_saturation_changed)
        saturation_layout.addWidget(self.slider_saturation)
        self.lbl_saturation_value = QLabel("50")
        self.lbl_saturation_value.setMinimumWidth(30)
        saturation_layout.addWidget(self.lbl_saturation_value)
        params_layout.addLayout(saturation_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Zoom Group
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QVBoxLayout()
        
        zoom_info_layout = QHBoxLayout()
        zoom_info_layout.addWidget(QLabel("Zoom Width:"))
        self.spin_zoom_width = QSpinBox()
        self.spin_zoom_width.setRange(0, 10000)
        self.spin_zoom_width.setValue(0)
        self.spin_zoom_width.setSuffix(" px")
        zoom_info_layout.addWidget(self.spin_zoom_width)
        
        zoom_info_layout.addWidget(QLabel("Zoom Height:"))
        self.spin_zoom_height = QSpinBox()
        self.spin_zoom_height.setRange(0, 10000)
        self.spin_zoom_height.setValue(0)
        self.spin_zoom_height.setSuffix(" px")
        zoom_info_layout.addWidget(self.spin_zoom_height)
        zoom_layout.addLayout(zoom_info_layout)
        
        zoom_note = QLabel("Note: Set to 0 to disable zoom")
        zoom_note.setStyleSheet("color: #888; font-size: 10px;")
        zoom_layout.addWidget(zoom_note)
        
        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)
        
        # Save/Load Settings
        save_group = QGroupBox("Settings Management")
        save_layout = QVBoxLayout()
        
        btn_save_layout = QHBoxLayout()
        self.btn_save_settings = QPushButton("Save Settings")
        self.btn_save_settings.clicked.connect(self._on_save_settings_clicked)
        btn_save_layout.addWidget(self.btn_save_settings)
        
        self.btn_load_settings = QPushButton("Load Settings")
        self.btn_load_settings.clicked.connect(self._on_load_settings_clicked)
        btn_save_layout.addWidget(self.btn_load_settings)
        
        self.btn_reset_settings = QPushButton("Reset to Default")
        self.btn_reset_settings.clicked.connect(self._on_reset_settings_clicked)
        btn_save_layout.addWidget(self.btn_reset_settings)
        
        save_layout.addLayout(btn_save_layout)
        
        self.lbl_settings_status = QLabel("Settings not saved")
        self.lbl_settings_status.setStyleSheet("color: #888; font-size: 10px;")
        save_layout.addWidget(self.lbl_settings_status)
        
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_camera_info_group(self) -> QGroupBox:
        info_group = QGroupBox("Camera Info")
        info_layout = QHBoxLayout()
        
        # Camera info labels trên cùng một hàng
        self.lbl_camera_type = QLabel("Type: -")
        self.lbl_camera_id = QLabel("ID: -")
        self.lbl_camera_status = QLabel("Status: Disconnected")
        
        info_layout.addWidget(self.lbl_camera_type)
        info_layout.addWidget(self.lbl_camera_id)
        info_layout.addWidget(self.lbl_camera_status)
        info_layout.addStretch()
        
        info_group.setLayout(info_layout)
        return info_group
    
    # ========== IView Implementation ==========
    
    def show_message(self, message: str, message_type: str = "info"):
        """Hiển thị message"""
        logger.info(f"Message [{message_type}]: {message}")
        
        if message_type == "error":
            QMessageBox.critical(self, "Error", message)
        elif message_type == "warning":
            QMessageBox.warning(self, "Warning", message)
        elif message_type == "success":
            QMessageBox.information(self, "Success", message)
        else:
            self.status_bar.showMessage(message, 3000)
    
    def update_status(self, status: str):
        """Cập nhật trạng thái"""
        logger.info(f"Status: {status}")
        self.status_bar.showMessage(f"Status: {status}")
        
        # Update button states based on status
        if status == "connected":
            # Connection: Ẩn Connect, hiện Disconnect
            self.btn_connect.setVisible(False)
            self.btn_disconnect.setVisible(True)
            self.btn_disconnect.setEnabled(True)
            
            # Streaming: Hiện Start, ẩn Stop
            self.btn_start_stream.setVisible(True)
            self.btn_start_stream.setEnabled(True)
            self.btn_stop_stream.setVisible(False)
            self.btn_capture.setEnabled(True)
            
        elif status == "disconnected" or status == "idle":
            # Connection: Hiện Connect, ẩn Disconnect
            self.btn_connect.setVisible(True)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setVisible(False)
            
            # Streaming: Ẩn cả Start và Stop
            self.btn_start_stream.setVisible(False)
            self.btn_stop_stream.setVisible(False)
            self.btn_capture.setEnabled(False)
            
            self.image_display.setText("No Camera Connected")
            
            # Template selection should still be enabled (can work without camera)
            if hasattr(self, 'combo_running_template'):
                self.combo_running_template.setEnabled(True)
            if hasattr(self, 'btn_load_running_template'):
                self.btn_load_running_template.setEnabled(True)
            if hasattr(self, 'btn_refresh_running_templates'):
                self.btn_refresh_running_templates.setEnabled(True)
            
        elif status == "capturing" or status == "streaming":
            # Connection: Vẫn hiện Disconnect
            self.btn_connect.setVisible(False)
            self.btn_disconnect.setVisible(True)
            
            # Streaming: Ẩn Start, hiện Stop
            self.btn_start_stream.setVisible(False)
            self.btn_stop_stream.setVisible(True)
            self.btn_stop_stream.setEnabled(True)
            self.btn_capture.setEnabled(True)
            
            
        elif status == "teaching":
            # Teaching mode
            self.btn_start_stream.setEnabled(False)
            self.btn_stop_stream.setEnabled(True)
            self.btn_capture.setEnabled(True)
            self.enable_teaching_controls(True)
            
        elif status == "running":
            # Running mode
            self.btn_start_stream.setEnabled(False)
            self.btn_stop_stream.setEnabled(True)
            self.btn_capture.setEnabled(True)
            self.chk_barcode_enabled.setEnabled(True)
            self.chk_show_regions.setEnabled(True)
    
    def display_image(self, image: np.ndarray):
        """Hiển thị ảnh"""
        try:
            # Convert BGR to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert NumPy array to QImage
            if len(image.shape) == 2:  # Grayscale
                height, width = image.shape
                bytes_per_line = width
                q_image = QImage(
                    image.data, width, height, bytes_per_line, 
                    QImage.Format_Grayscale8
                )
            else:  # Color
                height, width, channels = image.shape
                bytes_per_line = channels * width
                q_image = QImage(
                    image.data, width, height, bytes_per_line,
                    QImage.Format_RGB888
                )
            
            # Create pixmap
            pixmap = QPixmap.fromImage(q_image)
            
            # Display in image widget
            self.image_display.set_image(pixmap)
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
    
    def enable_controls(self, enabled: bool):
        """Enable/disable controls"""
        self.btn_connect.setEnabled(enabled)
        self.btn_disconnect.setEnabled(enabled)
        self.btn_start_stream.setEnabled(enabled)
        self.btn_stop_stream.setEnabled(enabled)
        self.btn_capture.setEnabled(enabled)
    
    def update_camera_info(self, info: dict):
        """Cập nhật thông tin camera"""
        try:
            if info is None:
                info = {}
            
            # Kiểm tra xem các label đã được khởi tạo chưa
            if not hasattr(self, 'lbl_camera_type'):
                logger.warning("lbl_camera_type not initialized, skipping update")
                return
            
            camera_type = info.get('type', '-')
            camera_id = info.get('camera_id', '-')
            is_connected = info.get('is_connected', False)
            is_grabbing = info.get('is_grabbing', False)
            
            self.lbl_camera_type.setText(f"Type: {camera_type}")
            self.lbl_camera_id.setText(f"ID: {camera_id}")
            
            if is_grabbing:
                status = "Streaming"
            elif is_connected:
                status = "Connected"
            else:
                status = "Disconnected"
            
            self.lbl_camera_status.setText(f"Status: {status}")
        except AttributeError as e:
            logger.error(f"Camera info labels not initialized: {e}", exc_info=True)
            # Không cố gắng set text nếu label chưa tồn tại
        except Exception as e:
            logger.error(f"Failed to update camera info: {e}", exc_info=True)
            # Chỉ set default values nếu label đã tồn tại
            if hasattr(self, 'lbl_camera_type'):
                try:
                    self.lbl_camera_type.setText("Type: -")
                    self.lbl_camera_id.setText("ID: -")
                    self.lbl_camera_status.setText("Status: Disconnected")
                except Exception:
                    pass
    
    # ========== Event Handlers ==========
    
    def _on_connect_clicked(self):
        """Handle connect button"""
        if self._presenter:
            self._presenter.on_connect_clicked()
    
    def _on_disconnect_clicked(self):
        """Handle disconnect button"""
        if self._presenter:
            self._presenter.on_disconnect_clicked()
    
    def _on_start_stream_clicked(self):
        """Handle start stream button"""
        if self._presenter:
            self._presenter.on_start_stream_clicked()
    
    def _on_stop_stream_clicked(self):
        """Handle stop stream button"""
        if self._presenter:
            self._presenter.on_stop_stream_clicked()
    
    def _on_capture_clicked(self):
        """Handle capture button"""
        if self._presenter:
            self._presenter.on_capture_clicked()
    
    def update_camera_settings_controls(self, settings: dict):
        """Update camera settings controls with loaded values"""
        if 'exposure_time' in settings:
            self.spin_exposure.setValue(settings['exposure_time'])
        if 'gain' in settings:
            self.spin_gain_setting.setValue(settings['gain'])
        if 'brightness' in settings:
            self.slider_brightness.setValue(settings['brightness'])
            self.lbl_brightness_value.setText(str(settings['brightness']))
        if 'contrast' in settings:
            self.slider_contrast.setValue(settings['contrast'])
            self.lbl_contrast_value.setText(str(settings['contrast']))
        if 'saturation' in settings:
            self.slider_saturation.setValue(settings['saturation'])
            self.lbl_saturation_value.setText(str(settings['saturation']))
        if 'zoom_width' in settings:
            self.spin_zoom_width.setValue(settings['zoom_width'])
        if 'zoom_height' in settings:
            self.spin_zoom_height.setValue(settings['zoom_height'])
    
    def _on_barcode_enabled_changed(self, state: int):
        """Handle barcode enabled checkbox change"""
        enabled = (state == 2)  # Qt.Checked = 2
        self.chk_show_regions.setEnabled(enabled)
        
        if self._presenter:
            self._presenter.on_barcode_enabled_changed(enabled)
    
    def _on_clear_barcode_clicked(self):
        """Handle clear barcode results button"""
        self.txt_barcode_results.clear()
    
    # ========== Template Mode Event Handlers (for editing templates) ==========
    
    def _on_select_template_clicked(self):
        """Handle select template region button"""
        logger.info("Select template button clicked")
        self._roi_selection_mode = 'template'
        self.image_display.start_roi_selection()
        self.status_bar.showMessage("Select template region: Click and drag on image")
    
    def _on_add_qr_roi_clicked(self):
        """Handle add QR ROI button"""
        logger.info("Add QR ROI button clicked")
        self._roi_selection_mode = 'qr_roi'
        self.image_display.start_roi_selection()
        self.status_bar.showMessage("Select QR ROI: Click and drag on image")
    
    def _on_roi_selected(self, x: int, y: int, width: int, height: int):
        """Handle ROI selected from image widget"""
        logger.info(f"ROI selected: ({x}, {y}, {width}x{height}), mode={self._roi_selection_mode}")
        
        if self._roi_selection_mode == 'template':
            # Notify presenter about template region (Recipe mode)
            if self._presenter:
                self._presenter.on_template_region_selected(x, y, width, height)
            # Update UI
            self.lbl_template_region.setText(f"({x}, {y}) - {width}x{height}")
            self.status_bar.showMessage(f"Template region selected: {width}x{height}")
            
        elif self._roi_selection_mode == 'qr_roi':
            # Notify presenter about QR ROI (Recipe mode)
            if self._presenter:
                roi_name = f"QR_{len(self.txt_qr_roi_list.toPlainText().split('\\n')) if self.txt_qr_roi_list.toPlainText() else 0}"
                self._presenter.on_qr_roi_added(roi_name, x, y, width, height)
            self.status_bar.showMessage(f"QR ROI added: {width}x{height}")
        
        elif self._roi_selection_mode == 'template_crop':
            # Notify presenter about crop region (Template mode) - có thể có scan barcode
            if self._presenter:
                from PySide6.QtWidgets import QInputDialog
                region_name, ok = QInputDialog.getText(
                    self, "Region Name", 
                    "Enter region name:",
                    text=f"Region_{len(self.txt_template_regions_list.toPlainText().split('\\n')) if self.txt_template_regions_list.toPlainText() else 0}"
                )
                if ok and region_name:
                    scan_barcode = self.chk_scan_barcode.isChecked()
                    self._presenter.on_template_crop_region_added(region_name, x, y, width, height, scan_barcode)
            scan_text = "with barcode scan" if self.chk_scan_barcode.isChecked() else "crop only"
            self.status_bar.showMessage(f"Region added ({scan_text}): {width}x{height}")
        
        # Reset mode
        self._roi_selection_mode = None
    
    def _on_save_recipe_clicked(self):
        """Handle save recipe button"""
        recipe_name = self.txt_recipe_name.text().strip()
        recipe_desc = self.txt_recipe_desc.text().strip()
        
        if not recipe_name:
            QMessageBox.warning(self, "Warning", "Please enter recipe name")
            return
        
        if self._presenter:
            self._presenter.on_save_recipe_clicked(recipe_name, recipe_desc)
    
    # ========== Running Mode Event Handlers ==========
    
    def _on_load_running_template_clicked(self):
        """Handle load template button (Running Mode)"""
        template_name = self.combo_running_template.currentText()
        if template_name == "-- No Template --":
            QMessageBox.warning(self, "Warning", "Please select a template")
            return
        
        if self._presenter:
            self._presenter.on_load_template_clicked(template_name)
    
    def _on_refresh_running_templates_clicked(self):
        """Handle refresh templates button (Running Mode)"""
        if self._presenter:
            self._presenter.on_refresh_templates_clicked()
    
    def _on_load_image_clicked(self):
        """Handle load image from file button (Template Mode - deprecated, use template mode)"""
        from PySide6.QtWidgets import QFileDialog
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Master Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if file_path:
            # Load image
            import cv2
            image = cv2.imread(file_path)
            
            if image is not None:
                # Display image
                self.display_image(image)
                
                # Notify presenter
                if self._presenter:
                    self._presenter.on_image_loaded_from_file(image, file_path)
                
                # Update label
                import os
                filename = os.path.basename(file_path)
                self.lbl_image_source.setText(f"Loaded: {filename}")
                self.status_bar.showMessage(f"Image loaded: {filename}")
            else:
                QMessageBox.warning(self, "Error", "Failed to load image file")
        else:
            logger.info("No file selected")
    
    def _on_load_test_image_clicked(self):
        """Handle load test image from file button (Running Mode)"""
        from PySide6.QtWidgets import QFileDialog
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Image for QR Detection",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if file_path:
            # Load image
            import cv2
            image = cv2.imread(file_path)
            
            if image is not None:
                # Display image
                self.display_image(image)
                
                # Notify presenter
                if self._presenter:
                    self._presenter.on_test_image_loaded(image, file_path)
                
                # Update label
                import os
                filename = os.path.basename(file_path)
                self.lbl_test_image_source.setText(f"Loaded: {filename}")
                self.status_bar.showMessage(f"Test image loaded: {filename}")
                
                # Enable process button
                self.btn_process_test_image.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", "Failed to load image file")
        else:
            logger.info("No file selected")
    
    def _on_process_test_image_clicked(self):
        """Handle process test image button"""
        if self._presenter:
            self._presenter.on_process_test_image_clicked()
    
    # ========== Template Mode Event Handlers ==========
    
    def _on_template_load_image_clicked(self):
        """Handle load image for template creation"""
        from PySide6.QtWidgets import QFileDialog
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Master Image for Template",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if file_path:
            # Load image
            import cv2
            image = cv2.imread(file_path)
            
            if image is not None:
                # Display image
                self.display_image(image)
                
                # Notify presenter
                if self._presenter:
                    self._presenter.on_template_image_loaded(image, file_path)
                
                # Update label
                import os
                filename = os.path.basename(file_path)
                self.lbl_template_image_source.setText(f"Loaded: {filename}")
                self.status_bar.showMessage(f"Template image loaded: {filename}")
                
                # Enable region button
                self.btn_add_crop_region.setEnabled(True)
                self.btn_save_template.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", "Failed to load image file")
        else:
            logger.info("No file selected")
    
    def _on_add_crop_region_clicked(self):
        """Handle add region button (crop + barcode dùng chung)"""
        logger.info("Add region button clicked")
        self._roi_selection_mode = 'template_crop'
        self.image_display.start_roi_selection()
        scan_barcode = "with barcode scan" if self.chk_scan_barcode.isChecked() else "crop only"
        self.status_bar.showMessage(f"Select region ({scan_barcode}): Click and drag on image")
    
    def _on_save_template_clicked(self):
        """Handle save template button"""
        template_name = self.txt_template_name.text().strip()
        template_desc = self.txt_template_desc.text().strip()
        
        if not template_name:
            QMessageBox.warning(self, "Warning", "Please enter template name")
            return
        
        if self._presenter:
            self._presenter.on_save_template_clicked(template_name, template_desc)
    
    def _on_load_template_clicked(self):
        """Handle load template button"""
        template_name = self.combo_template.currentText()
        if template_name == "-- No Template --":
            QMessageBox.warning(self, "Warning", "Please select a template")
            return
        
        if self._presenter:
            self._presenter.on_load_template_clicked(template_name)
    
    def _on_refresh_templates_clicked(self):
        """Handle refresh templates button"""
        if self._presenter:
            self._presenter.on_refresh_templates_clicked()
    
    # ========== Setting Mode Event Handlers ==========
    
    def _on_exposure_changed(self, value: int):
        """Handle exposure time changed"""
        if self._presenter:
            self._presenter.on_camera_parameter_changed('ExposureTime', value)
    
    def _on_gain_setting_changed(self, value: int):
        """Handle gain changed (Setting mode)"""
        if self._presenter:
            self._presenter.on_camera_parameter_changed('Gain', value)
    
    def _on_brightness_changed(self, value: int):
        """Handle brightness (gamma) changed"""
        self.lbl_brightness_value.setText(str(value))
        if self._presenter:
            self._presenter.on_camera_parameter_changed('Gamma', value)
    
    def _on_contrast_changed(self, value: int):
        """Handle contrast changed"""
        self.lbl_contrast_value.setText(str(value))
        if self._presenter:
            self._presenter.on_camera_parameter_changed('Contrast', value)
    
    def _on_saturation_changed(self, value: int):
        """Handle saturation changed"""
        self.lbl_saturation_value.setText(str(value))
        if self._presenter:
            self._presenter.on_camera_parameter_changed('Saturation', value)
    
    def _on_save_settings_clicked(self):
        """Handle save settings button"""
        if self._presenter:
            settings = {
                'exposure_time': self.spin_exposure.value(),
                'gain': self.spin_gain_setting.value(),
                'brightness': self.slider_brightness.value(),
                'contrast': self.slider_contrast.value(),
                'saturation': self.slider_saturation.value(),
                'zoom_width': self.spin_zoom_width.value(),
                'zoom_height': self.spin_zoom_height.value()
            }
            if self._presenter.on_save_camera_settings(settings):
                self.lbl_settings_status.setText("Settings saved successfully")
                self.lbl_settings_status.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.lbl_settings_status.setText("Failed to save settings")
                self.lbl_settings_status.setStyleSheet("color: red; font-size: 10px;")
    
    def _on_load_settings_clicked(self):
        """Handle load settings button"""
        if self._presenter:
            settings = self._presenter.on_load_camera_settings()
            if settings:
                self.spin_exposure.setValue(settings.get('exposure_time', 10000))
                self.spin_gain_setting.setValue(settings.get('gain', 0))
                self.slider_brightness.setValue(settings.get('brightness', 50))
                self.slider_contrast.setValue(settings.get('contrast', 0))
                self.slider_saturation.setValue(settings.get('saturation', 50))
                self.spin_zoom_width.setValue(settings.get('zoom_width', 0))
                self.spin_zoom_height.setValue(settings.get('zoom_height', 0))
                self.lbl_settings_status.setText("Settings loaded successfully")
                self.lbl_settings_status.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.lbl_settings_status.setText("No saved settings found")
                self.lbl_settings_status.setStyleSheet("color: #888; font-size: 10px;")
    
    def _on_reset_settings_clicked(self):
        """Handle reset settings button"""
        self.spin_exposure.setValue(10000)
        self.spin_gain_setting.setValue(0)
        self.slider_brightness.setValue(50)
        self.slider_contrast.setValue(0)
        self.slider_saturation.setValue(50)
        self.spin_zoom_width.setValue(0)
        self.spin_zoom_height.setValue(0)
        self.lbl_settings_status.setText("Settings reset to default")
        self.lbl_settings_status.setStyleSheet("color: #888; font-size: 10px;")
    
    def _on_template_load_test_image_clicked(self):
        """Handle load test image for template processing"""
        from PySide6.QtWidgets import QFileDialog
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Image for Template Processing",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if file_path:
            # Load image
            import cv2
            image = cv2.imread(file_path)
            
            if image is not None:
                # Display image
                self.display_image(image)
                
                # Notify presenter
                if self._presenter:
                    self._presenter.on_template_test_image_loaded(image, file_path)
                
                # Update label
                import os
                filename = os.path.basename(file_path)
                self.lbl_template_test_image.setText(f"Loaded: {filename}")
                self.status_bar.showMessage(f"Test image loaded: {filename}")
                
                # Enable process button
                self.btn_process_template.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", "Failed to load image file")
        else:
            logger.info("No file selected")
    
    def _on_process_template_clicked(self):
        """Handle process template button"""
        if self._presenter:
            self._presenter.on_process_template_clicked()
    
    def update_template_list(self, templates: list):
        """Update template combo box (both running and template mode)"""
        # Update running mode combo
        if hasattr(self, 'combo_running_template'):
            self.combo_running_template.clear()
            self.combo_running_template.addItem("-- No Template --")
            for template in templates:
                self.combo_running_template.addItem(template)
            # Ensure combo is enabled (can select template even without camera)
            self.combo_running_template.setEnabled(True)
            # Ensure load button is enabled
            if hasattr(self, 'btn_load_running_template'):
                self.btn_load_running_template.setEnabled(True)
            if hasattr(self, 'btn_refresh_running_templates'):
                self.btn_refresh_running_templates.setEnabled(True)
        
        # Update template mode combo (if exists)
        if hasattr(self, 'combo_template'):
            self.combo_template.clear()
            self.combo_template.addItem("-- No Template --")
            for template in templates:
                self.combo_template.addItem(template)
    
    def update_template_regions_list(self, regions_text: str):
        """Update template regions list display"""
        self.txt_template_regions_list.setPlainText(regions_text)
    
    def update_current_template_info(self, info: str):
        """Update current template info label (for both modes)"""
        # Update running mode label
        if hasattr(self, 'lbl_current_template'):
            self.lbl_current_template.setText(info)
        # Update template mode label
        if hasattr(self, 'lbl_current_template_info'):
            self.lbl_current_template_info.setText(info)
    
    def update_template_results(self, results_text: str):
        """Update template processing results"""
        self.txt_template_results.setPlainText(results_text)
    
    def get_show_regions_enabled(self) -> bool:
        """Get show regions checkbox state"""
        return self.chk_show_regions.isChecked()
    
    def update_barcode_results(self, results: dict):
        """Update barcode detection results display"""
        if not results:
            self.txt_barcode_results.setPlainText("No barcodes detected")
            return
        
        text = ""
        for region_name, barcode_list in results.items():
            if barcode_list:
                for barcode_data in barcode_list:
                    text += f"[{region_name}] {barcode_data}\n"
            else:
                text += f"[{region_name}] No barcode found\n"
        
        self.txt_barcode_results.setPlainText(text.strip())
    
    def update_current_template_info(self, template_info: str):
        """Update current template info label"""
        self.lbl_current_template.setText(template_info)
    
    def update_template_region_info(self, info: str):
        """Update template region label"""
        self.lbl_template_region.setText(info)
    
    def update_qr_roi_list(self, qr_rois: list):
        """Update QR ROI list display"""
        if not qr_rois:
            self.txt_qr_roi_list.setPlainText("No QR ROI regions")
            return
        
        text = ""
        for i, roi in enumerate(qr_rois):
            text += f"{i+1}. {roi['name']}: ({roi['x']}, {roi['y']}, {roi['w']}x{roi['h']})\n"
        
        self.txt_qr_roi_list.setPlainText(text.strip())
    
    
    def showEvent(self, event):
        """Window shown"""
        super().showEvent(event)
        if self._presenter:
            self._presenter.on_view_ready()
    
    def closeEvent(self, event):
        """Window closing"""
        if self._presenter:
            self._presenter.on_view_closing()
        event.accept()

