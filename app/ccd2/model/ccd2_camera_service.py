"""
CCD2 Camera Service - Hoàn toàn độc lập với CCD1
Quản lý camera CCD2, chạy trong QThread riêng
"""
import logging
from typing import Optional, Dict, Any
import numpy as np
from PySide6.QtCore import QThread, Signal
import sys
import os

# Import shared camera classes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app.shared.model.camera.camera_connection_service import CameraConnectionService

logger = logging.getLogger(__name__)


class CCD2CameraService(QThread):
    """
    CCD2 Camera Service - Chạy trong thread riêng
    - Tự quản lý connect, streaming
    - Emit frame qua signal
    """
    
    # Signals
    frame_captured = Signal(np.ndarray)  # Emit frame đã capture
    status_changed = Signal(str)  # idle, connecting, connected, streaming, error
    error_occurred = Signal(str)  # Emit error message
    
    def __init__(self, camera_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._camera_config = camera_config
        self._camera_id = str(camera_config.get('ip', '1'))
        self._running = False
        self._camera_service = CameraConnectionService()
        logger.info(f"CCD2CameraService initialized with camera_id={self._camera_id}")
    
    def run(self):
        """Thread chính - connect và streaming"""
        try:
            self.status_changed.emit('connecting')
            logger.info(f"[CCD2] Connecting to camera {self._camera_id}...")
            
            # Create camera instance
            if not self._camera_service.create_camera(self._camera_id, self._camera_config):
                self.error_occurred.emit("Failed to create CCD2 camera instance")
                self.status_changed.emit('error')
                return
            
            # Connect
            if not self._camera_service.connect():
                self.error_occurred.emit("Failed to connect CCD2 camera")
                self.status_changed.emit('error')
                return
            
            self.status_changed.emit('connected')
            logger.info("[CCD2] Camera connected successfully")
            
            # Start streaming
            if not self._camera_service.start_streaming():
                self.error_occurred.emit("Failed to start CCD2 streaming")
                self.status_changed.emit('error')
                return
            
            self.status_changed.emit('streaming')
            logger.info("[CCD2] Streaming started")
            
            self._running = True
            
            # Main loop - capture frames
            while self._running:
                frame = self._camera_service.get_frame(timeout_ms=100)
                if frame is not None:
                    try:
                        self.frame_captured.emit(frame)
                    except Exception as e:
                        logger.error(f"[CCD2] Failed to emit frame: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"[CCD2] Runtime error: {e}", exc_info=True)
            self.error_occurred.emit(f"CCD2 error: {str(e)}")
            self.status_changed.emit('error')
            
        finally:
            # Cleanup
            try:
                self._camera_service.stop_streaming()
                self._camera_service.disconnect()
                self._camera_service.cleanup()
            except Exception as e:
                logger.error(f"[CCD2] Cleanup error: {e}", exc_info=True)
            
            self.status_changed.emit('idle')
            logger.info("[CCD2] Service stopped and cleaned up")
    
    def stop(self):
        """Dừng thread"""
        logger.info("[CCD2] Stop requested")
        self._running = False
    
    def get_camera_info(self) -> Dict[str, Any]:
        """Lấy thông tin camera"""
        if self._camera_service:
            return self._camera_service.get_camera_info()
        return {}
