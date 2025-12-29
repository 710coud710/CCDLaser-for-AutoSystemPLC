"""
Main View - Giao diện chính của ứng dụng
Sử dụng PySide6 (Qt)
"""
import logging
from typing import Optional
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox, QStatusBar,
    QSlider, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from .view_interface import IView, IPresenter

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
        
        # Right panel - Controls
        right_panel = self._create_control_panel()
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
        
        # Label hiển thị ảnh
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 2px solid #555;
                color: #888;
            }
        """)
        self.image_label.setText("No Camera Connected")
        
        layout.addWidget(self.image_label)
        
        # Info label
        self.info_label = QLabel("Camera: Not connected")
        self.info_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.info_label)
        
        group.setLayout(layout)
        return group
    
    def _create_control_panel(self) -> QWidget:
        """Tạo panel điều khiển"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Connection group
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        
        self.btn_connect = QPushButton("Connect Camera")
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        conn_layout.addWidget(self.btn_connect)
        
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)
        self.btn_disconnect.setEnabled(False)
        conn_layout.addWidget(self.btn_disconnect)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Streaming group
        stream_group = QGroupBox("Streaming")
        stream_layout = QVBoxLayout()
        
        self.btn_start_stream = QPushButton("Start Stream")
        self.btn_start_stream.clicked.connect(self._on_start_stream_clicked)
        self.btn_start_stream.setEnabled(False)
        stream_layout.addWidget(self.btn_start_stream)
        
        self.btn_stop_stream = QPushButton("Stop Stream")
        self.btn_stop_stream.clicked.connect(self._on_stop_stream_clicked)
        self.btn_stop_stream.setEnabled(False)
        stream_layout.addWidget(self.btn_stop_stream)
        
        stream_group.setLayout(stream_layout)
        layout.addWidget(stream_group)
        
        # Capture group
        capture_group = QGroupBox("Capture")
        capture_layout = QVBoxLayout()
        
        self.btn_capture = QPushButton("Capture Image")
        self.btn_capture.clicked.connect(self._on_capture_clicked)
        self.btn_capture.setEnabled(False)
        capture_layout.addWidget(self.btn_capture)
        
        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)
        
        # Camera info
        info_group = QGroupBox("Camera Info")
        info_layout = QVBoxLayout()
        
        self.lbl_camera_type = QLabel("Type: -")
        self.lbl_camera_id = QLabel("ID: -")
        self.lbl_camera_status = QLabel("Status: Disconnected")
        
        info_layout.addWidget(self.lbl_camera_type)
        info_layout.addWidget(self.lbl_camera_id)
        info_layout.addWidget(self.lbl_camera_status)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Camera parameters
        params_group = QGroupBox("Camera Parameters")
        params_layout = QVBoxLayout()
        
        # Gain control
        gain_label = QLabel("Gain:")
        params_layout.addWidget(gain_label)
        
        gain_control_layout = QHBoxLayout()
        
        # Gain slider (0-100)
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setMinimum(0)
        self.gain_slider.setMaximum(100)
        self.gain_slider.setValue(0)
        self.gain_slider.setEnabled(False)
        self.gain_slider.valueChanged.connect(self._on_gain_slider_changed)
        gain_control_layout.addWidget(self.gain_slider)
        
        # Gain spinbox
        self.gain_spinbox = QSpinBox()
        self.gain_spinbox.setMinimum(0)
        self.gain_spinbox.setMaximum(100)
        self.gain_spinbox.setValue(0)
        self.gain_spinbox.setEnabled(False)
        self.gain_spinbox.valueChanged.connect(self._on_gain_spinbox_changed)
        gain_control_layout.addWidget(self.gain_spinbox)
        
        params_layout.addLayout(gain_control_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Spacer
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
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
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.btn_start_stream.setEnabled(True)
            self.btn_stop_stream.setEnabled(False)
            self.btn_capture.setEnabled(False)
            self.gain_slider.setEnabled(True)
            self.gain_spinbox.setEnabled(True)
            
        elif status == "disconnected" or status == "idle":
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.btn_start_stream.setEnabled(False)
            self.btn_stop_stream.setEnabled(False)
            self.btn_capture.setEnabled(False)
            self.gain_slider.setEnabled(False)
            self.gain_spinbox.setEnabled(False)
            self.image_label.setText("No Camera Connected")
            
        elif status == "capturing":
            self.btn_start_stream.setEnabled(False)
            self.btn_stop_stream.setEnabled(True)
            self.btn_capture.setEnabled(True)
            self.gain_slider.setEnabled(True)
            self.gain_spinbox.setEnabled(True)
    
    def display_image(self, image: np.ndarray):
        """Hiển thị ảnh"""
        try:
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
            
            # Scale to fit label
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
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
    
    def _on_gain_slider_changed(self, value: int):
        """Handle gain slider change"""
        # Update spinbox without triggering its signal
        self.gain_spinbox.blockSignals(True)
        self.gain_spinbox.setValue(value)
        self.gain_spinbox.blockSignals(False)
        
        # Notify presenter
        if self._presenter:
            self._presenter.on_gain_changed(value)
    
    def _on_gain_spinbox_changed(self, value: int):
        """Handle gain spinbox change"""
        # Update slider without triggering its signal
        self.gain_slider.blockSignals(True)
        self.gain_slider.setValue(value)
        self.gain_slider.blockSignals(False)
        
        # Notify presenter
        if self._presenter:
            self._presenter.on_gain_changed(value)
    
    def set_gain_value(self, value: int):
        """Set gain value from presenter"""
        self.gain_slider.blockSignals(True)
        self.gain_spinbox.blockSignals(True)
        self.gain_slider.setValue(value)
        self.gain_spinbox.setValue(value)
        self.gain_slider.blockSignals(False)
        self.gain_spinbox.blockSignals(False)
    
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

