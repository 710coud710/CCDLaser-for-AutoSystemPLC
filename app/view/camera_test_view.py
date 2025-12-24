"""
Camera Test View - Giao diện test camera từng bước
Mỗi bước có nút riêng để test độc lập
"""
import logging
from typing import Optional
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QTextEdit, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QFont

logger = logging.getLogger(__name__)


class CameraTestView(QMainWindow):
    """
    Camera Test Window - Test từng bước kết nối camera
    
    [1] Load SDK        ← Import mvsdk
    [2] Enumerate       ← Quét cameras
    [3] Init Camera     ← Mở camera
    [4] Configure       ← Cấu hình
    [5] Start Grab      ← Bắt đầu stream
    [6] Get Frame       ← Lấy 1 frame
    [7] Stop Grab       ← Dừng stream
    [8] Close Camera    ← Đóng camera
    """
    
    # Signals
    sig_step1_clicked = Signal()  # Load SDK
    sig_step2_clicked = Signal()  # Enumerate
    sig_step3_clicked = Signal()  # Init camera
    sig_step4_clicked = Signal()  # Configure
    sig_step5_clicked = Signal()  # Start grab
    sig_step6_clicked = Signal()  # Get frame
    sig_step7_clicked = Signal()  # Stop grab
    sig_step8_clicked = Signal()  # Close camera
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        logger.info("CameraTestView initialized")
    
    def _init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("CCDLaser - Camera Test (Step by Step)")
        self.setMinimumSize(1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - Horizontal splitter
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Control panel
        left_panel = self._create_control_panel()
        splitter.addWidget(left_panel)
        
        # Right: Display panel
        right_panel = self._create_display_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (30% left, 70% right)
        splitter.setSizes([420, 980])
        
        main_layout.addWidget(splitter)
        
        logger.info("UI initialized")
    
    def _create_control_panel(self) -> QWidget:
        """Tạo control panel với các nút test"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Camera Test Steps")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Step 1: Load SDK
        step1_group = QGroupBox("[1] Load SDK")
        step1_layout = QVBoxLayout()
        self.btn_step1 = QPushButton("Load SDK (mvsdk.py)")
        self.btn_step1.clicked.connect(self.sig_step1_clicked.emit)
        self.btn_step1.setMinimumHeight(40)
        step1_layout.addWidget(self.btn_step1)
        self.lbl_step1_status = QLabel("Status: Not loaded")
        self.lbl_step1_status.setStyleSheet("color: gray;")
        step1_layout.addWidget(self.lbl_step1_status)
        step1_group.setLayout(step1_layout)
        layout.addWidget(step1_group)
        
        # Step 2: Enumerate
        step2_group = QGroupBox("[2] Enumerate Cameras")
        step2_layout = QVBoxLayout()
        self.btn_step2 = QPushButton("Scan Cameras")
        self.btn_step2.clicked.connect(self.sig_step2_clicked.emit)
        self.btn_step2.setMinimumHeight(40)
        self.btn_step2.setEnabled(False)
        step2_layout.addWidget(self.btn_step2)
        self.lbl_step2_status = QLabel("Status: -")
        self.lbl_step2_status.setStyleSheet("color: gray;")
        step2_layout.addWidget(self.lbl_step2_status)
        step2_group.setLayout(step2_layout)
        layout.addWidget(step2_group)
        
        # Step 3: Init Camera
        step3_group = QGroupBox("[3] Initialize Camera")
        step3_layout = QVBoxLayout()
        self.btn_step3 = QPushButton("Open Camera (cam2)")
        self.btn_step3.clicked.connect(self.sig_step3_clicked.emit)
        self.btn_step3.setMinimumHeight(40)
        self.btn_step3.setEnabled(False)
        step3_layout.addWidget(self.btn_step3)
        self.lbl_step3_status = QLabel("Status: -")
        self.lbl_step3_status.setStyleSheet("color: gray;")
        step3_layout.addWidget(self.lbl_step3_status)
        step3_group.setLayout(step3_layout)
        layout.addWidget(step3_group)
        
        # Step 4: Configure
        step4_group = QGroupBox("[4] Configure Camera")
        step4_layout = QVBoxLayout()
        self.btn_step4 = QPushButton("Set Parameters")
        self.btn_step4.clicked.connect(self.sig_step4_clicked.emit)
        self.btn_step4.setMinimumHeight(40)
        self.btn_step4.setEnabled(False)
        step4_layout.addWidget(self.btn_step4)
        self.lbl_step4_status = QLabel("Status: -")
        self.lbl_step4_status.setStyleSheet("color: gray;")
        step4_layout.addWidget(self.lbl_step4_status)
        step4_group.setLayout(step4_layout)
        layout.addWidget(step4_group)
        
        # Step 5: Start Grab
        step5_group = QGroupBox("[5] Start Grabbing")
        step5_layout = QVBoxLayout()
        self.btn_step5 = QPushButton("Start Stream")
        self.btn_step5.clicked.connect(self.sig_step5_clicked.emit)
        self.btn_step5.setMinimumHeight(40)
        self.btn_step5.setEnabled(False)
        step5_layout.addWidget(self.btn_step5)
        self.lbl_step5_status = QLabel("Status: -")
        self.lbl_step5_status.setStyleSheet("color: gray;")
        step5_layout.addWidget(self.lbl_step5_status)
        step5_group.setLayout(step5_layout)
        layout.addWidget(step5_group)
        
        # Step 6: Get Frame
        step6_group = QGroupBox("[6] Capture Frame")
        step6_layout = QVBoxLayout()
        self.btn_step6 = QPushButton("Get 1 Frame")
        self.btn_step6.clicked.connect(self.sig_step6_clicked.emit)
        self.btn_step6.setMinimumHeight(40)
        self.btn_step6.setEnabled(False)
        step6_layout.addWidget(self.btn_step6)
        self.lbl_step6_status = QLabel("Status: -")
        self.lbl_step6_status.setStyleSheet("color: gray;")
        step6_layout.addWidget(self.lbl_step6_status)
        step6_group.setLayout(step6_layout)
        layout.addWidget(step6_group)
        
        # Step 7: Stop Grab
        step7_group = QGroupBox("[7] Stop Grabbing")
        step7_layout = QVBoxLayout()
        self.btn_step7 = QPushButton("Stop Stream")
        self.btn_step7.clicked.connect(self.sig_step7_clicked.emit)
        self.btn_step7.setMinimumHeight(40)
        self.btn_step7.setEnabled(False)
        step7_layout.addWidget(self.btn_step7)
        self.lbl_step7_status = QLabel("Status: -")
        self.lbl_step7_status.setStyleSheet("color: gray;")
        step7_layout.addWidget(self.lbl_step7_status)
        step7_group.setLayout(step7_layout)
        layout.addWidget(step7_group)
        
        # Step 8: Close Camera
        step8_group = QGroupBox("[8] Close Camera")
        step8_layout = QVBoxLayout()
        self.btn_step8 = QPushButton("Disconnect")
        self.btn_step8.clicked.connect(self.sig_step8_clicked.emit)
        self.btn_step8.setMinimumHeight(40)
        self.btn_step8.setEnabled(False)
        step8_layout.addWidget(self.btn_step8)
        self.lbl_step8_status = QLabel("Status: -")
        self.lbl_step8_status.setStyleSheet("color: gray;")
        step8_layout.addWidget(self.lbl_step8_status)
        step8_group.setLayout(step8_layout)
        layout.addWidget(step8_group)
        
        # Spacer
        layout.addStretch()
        
        # Reset button
        self.btn_reset = QPushButton("Reset All")
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        self.btn_reset.setStyleSheet("background-color: #dc3545; color: white;")
        self.btn_reset.setMinimumHeight(40)
        layout.addWidget(self.btn_reset)
        
        widget.setLayout(layout)
        return widget
    
    def _create_display_panel(self) -> QWidget:
        """Tạo display panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Image display
        image_group = QGroupBox("Camera View")
        image_layout = QVBoxLayout()
        
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
        self.image_label.setText("No Image")
        image_layout.addWidget(self.image_label)
        
        # Image info
        self.lbl_image_info = QLabel("Image info: -")
        self.lbl_image_info.setStyleSheet("color: #888; padding: 5px;")
        image_layout.addWidget(self.lbl_image_info)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group, stretch=2)
        
        # Log display
        log_group = QGroupBox("Log Output")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, stretch=1)
        
        widget.setLayout(layout)
        return widget
    
    # ========== Public methods to update UI ==========
    
    def update_step_status(self, step: int, status: str, success: bool = True):
        """
        Cập nhật status của step
        Args:
            step: 1-8
            status: Text hiển thị
            success: True=green, False=red
        """
        color = "green" if success else "red"
        
        if step == 1:
            self.lbl_step1_status.setText(f"Status: {status}")
            self.lbl_step1_status.setStyleSheet(f"color: {color};")
        elif step == 2:
            self.lbl_step2_status.setText(f"Status: {status}")
            self.lbl_step2_status.setStyleSheet(f"color: {color};")
        elif step == 3:
            self.lbl_step3_status.setText(f"Status: {status}")
            self.lbl_step3_status.setStyleSheet(f"color: {color};")
        elif step == 4:
            self.lbl_step4_status.setText(f"Status: {status}")
            self.lbl_step4_status.setStyleSheet(f"color: {color};")
        elif step == 5:
            self.lbl_step5_status.setText(f"Status: {status}")
            self.lbl_step5_status.setStyleSheet(f"color: {color};")
        elif step == 6:
            self.lbl_step6_status.setText(f"Status: {status}")
            self.lbl_step6_status.setStyleSheet(f"color: {color};")
        elif step == 7:
            self.lbl_step7_status.setText(f"Status: {status}")
            self.lbl_step7_status.setStyleSheet(f"color: {color};")
        elif step == 8:
            self.lbl_step8_status.setText(f"Status: {status}")
            self.lbl_step8_status.setStyleSheet(f"color: {color};")
    
    def enable_step(self, step: int, enabled: bool = True):
        """Enable/disable button của step"""
        if step == 1:
            self.btn_step1.setEnabled(enabled)
        elif step == 2:
            self.btn_step2.setEnabled(enabled)
        elif step == 3:
            self.btn_step3.setEnabled(enabled)
        elif step == 4:
            self.btn_step4.setEnabled(enabled)
        elif step == 5:
            self.btn_step5.setEnabled(enabled)
        elif step == 6:
            self.btn_step6.setEnabled(enabled)
        elif step == 7:
            self.btn_step7.setEnabled(enabled)
        elif step == 8:
            self.btn_step8.setEnabled(enabled)
    
    def append_log(self, message: str):
        """Thêm log message"""
        self.log_text.append(message)
        # Auto scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
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
            
            # Update image info
            info = f"Size: {width}x{height}, Type: {image.dtype}, Min: {image.min()}, Max: {image.max()}, Mean: {image.mean():.1f}"
            self.lbl_image_info.setText(info)
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
    
    def clear_image(self):
        """Clear image display"""
        self.image_label.clear()
        self.image_label.setText("No Image")
        self.lbl_image_info.setText("Image info: -")
    
    def _on_reset_clicked(self):
        """Reset button clicked"""
        # Reset all status
        for i in range(1, 9):
            self.update_step_status(i, "-", success=True)
            self.enable_step(i, False)
        
        # Enable step 1
        self.enable_step(1, True)
        
        # Clear log and image
        self.log_text.clear()
        self.clear_image()
        
        logger.info("UI reset")
    
    def closeEvent(self, event):
        """Window closing"""
        logger.info("CameraTestView closing")
        event.accept()

