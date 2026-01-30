"""
CCD1 View - Giao diện riêng cho CCD1
Hiển thị ảnh từ camera CCD1 và thông tin trạng thái
"""
import logging
import numpy as np
import cv2
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
import sys
import os

# Import shared widget
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app.shared.view.image_display_widget import ImageDisplayWidget

logger = logging.getLogger(__name__)


class CCD1View(QWidget):
    """
    View riêng cho CCD1
    - Hiển thị ảnh từ CCD1
    - Nút Start/Stop
    - Status bar
    """
    
    # Signals
    start_requested = Signal()
    stop_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        logger.info("CCD1View initialized")
    
    def _init_ui(self):
        """Khởi tạo giao diện CCD1"""
        layout = QVBoxLayout(self)
        
        # === Group: CCD1 Camera View ===
        group_camera = QGroupBox("CCD1 - Camera View")
        layout_camera = QVBoxLayout()
        
        # Image display
        self.image_display = ImageDisplayWidget()
        self.image_display.setMinimumSize(640, 480)
        layout_camera.addWidget(self.image_display)
        
        # Info label
        self.info_label = QLabel("CCD1: Not started")
        self.info_label.setStyleSheet("color: #888; padding: 5px;")
        layout_camera.addWidget(self.info_label)
        
        group_camera.setLayout(layout_camera)
        layout.addWidget(group_camera)
        
        # === Control buttons ===
        control_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("Start CCD1")
        self.btn_start.clicked.connect(self.start_requested.emit)
        control_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("Stop CCD1")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_stop.setEnabled(False)
        control_layout.addWidget(self.btn_stop)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # === Status text ===
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setPlaceholderText("CCD1 status messages...")
        layout.addWidget(self.status_text)
    
    def display_image(self, frame: np.ndarray):
        """Hiển thị ảnh từ CCD1"""
        try:
            self.image_display.display_image(frame)
        except Exception as e:
            logger.error(f"Failed to display CCD1 image: {e}", exc_info=True)
    
    def update_status(self, status: str):
        """Cập nhật trạng thái"""
        status_map = {
            'idle': ('Not started', '#888'),
            'connecting': ('Connecting...', '#FFA500'),
            'connected': ('Connected', '#00FF00'),
            'streaming': ('Streaming', '#00FF00'),
            'error': ('Error', '#FF0000')
        }
        
        text, color = status_map.get(status, (status, '#888'))
        self.info_label.setText(f"CCD1: {text}")
        self.info_label.setStyleSheet(f"color: {color}; padding: 5px; font-weight: bold;")
        
        # Enable/disable buttons
        if status in ['idle', 'error']:
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
        elif status in ['connecting', 'connected', 'streaming']:
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
    
    def append_log(self, message: str):
        """Thêm log message"""
        self.status_text.append(message)
        # Auto scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
