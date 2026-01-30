"""
CCD2 Presenter - Logic điều khiển riêng cho CCD2
Kết nối CCD2 View và CCD2 Model
"""
import logging
from typing import Optional, Dict, Any
import numpy as np
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class CCD2Presenter(QObject):
    """
    Presenter riêng cho CCD2
    - Quản lý CCD2CameraService (thread)
    - Xử lý logic CCD2
    - Cập nhật CCD2View
    """
    
    def __init__(self, view, camera_service):
        super().__init__()
        self._view = view
        self._camera_service = camera_service
        
        # Connect view signals
        self._view.start_requested.connect(self.on_start_clicked)
        self._view.stop_requested.connect(self.on_stop_clicked)
        
        # Connect camera service signals
        self._camera_service.frame_captured.connect(self.on_frame_captured)
        self._camera_service.status_changed.connect(self.on_status_changed)
        self._camera_service.error_occurred.connect(self.on_error_occurred)
        
        logger.info("CCD2Presenter initialized")
    
    def on_start_clicked(self):
        """User click Start CCD2"""
        logger.info("[CCD2] Start button clicked")
        try:
            self._camera_service.start()
            self._view.append_log("[CCD2] Starting camera service...")
        except Exception as e:
            logger.error(f"[CCD2] Failed to start: {e}", exc_info=True)
            self._view.append_log(f"[CCD2] ERROR: {e}")
    
    def on_stop_clicked(self):
        """User click Stop CCD2"""
        logger.info("[CCD2] Stop button clicked")
        try:
            self._camera_service.stop()
            self._camera_service.wait(3000)  # Wait max 3s
            self._view.append_log("[CCD2] Camera service stopped")
        except Exception as e:
            logger.error(f"[CCD2] Failed to stop: {e}", exc_info=True)
            self._view.append_log(f"[CCD2] ERROR: {e}")
    
    def on_frame_captured(self, frame: np.ndarray):
        """Nhận frame từ camera service"""
        try:
            # Display frame lên view
            self._view.display_image(frame)
        except Exception as e:
            logger.error(f"[CCD2] Error handling frame: {e}", exc_info=True)
    
    def on_status_changed(self, status: str):
        """Camera status changed"""
        logger.info(f"[CCD2] Status changed: {status}")
        self._view.update_status(status)
        self._view.append_log(f"[CCD2] Status: {status}")
    
    def on_error_occurred(self, error_msg: str):
        """Camera error occurred"""
        logger.error(f"[CCD2] Error: {error_msg}")
        self._view.append_log(f"[CCD2] ERROR: {error_msg}")
    
    def cleanup(self):
        """Cleanup khi thoát"""
        logger.info("[CCD2] Cleaning up presenter...")
        try:
            if self._camera_service.isRunning():
                self._camera_service.stop()
                self._camera_service.wait(3000)
        except Exception as e:
            logger.error(f"[CCD2] Cleanup error: {e}", exc_info=True)
