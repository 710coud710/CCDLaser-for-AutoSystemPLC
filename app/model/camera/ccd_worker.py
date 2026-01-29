"""
CCD Worker - QThread wrapper for an independent MindVision CCD camera.

Mỗi CCD sẽ chạy trong một QThread riêng, tự connect / streaming và
emit frame về UI qua signal, giúp 2 CCD hoạt động độc lập.
"""

import logging
from typing import Optional, Dict, Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from .camera_connection_service import CameraConnectionService

logger = logging.getLogger(__name__)


class CCDWorker(QThread):
    """
    QThread quản lý 1 CCD độc lập.

    - Tự tạo CameraConnectionService nội bộ
    - Connect → start_streaming → loop get_frame()
    - Emit signal frameCaptured cho mỗi frame
    """

    frameCaptured = Signal(np.ndarray)

    def __init__(self, camera_id: str, camera_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self._camera_id = str(camera_id)
        self._camera_config = camera_config or {}
        self._running = False
        self._camera_service = CameraConnectionService()

    def run(self):
        """
        Hàm chạy trong thread:
        - Tạo camera
        - Connect
        - Start streaming
        - Vòng lặp lấy frame và emit
        """
        logger.info(f"CCDWorker starting for camera_id={self._camera_id}")
        try:
            # Tạo camera instance
            if not self._camera_service.create_camera(self._camera_id, self._camera_config):
                logger.error("CCDWorker: Failed to create camera instance")
                return

            # Connect camera
            if not self._camera_service.connect():
                logger.error("CCDWorker: Failed to connect camera")
                return

            # Start streaming
            if not self._camera_service.start_streaming():
                logger.error("CCDWorker: Failed to start streaming")
                return

            self._running = True
            logger.info("CCDWorker streaming loop started")

            while self._running:
                frame = self._camera_service.get_frame(timeout_ms=100)
                if frame is None:
                    continue
                try:
                    self.frameCaptured.emit(frame)
                except Exception as e:
                    logger.error(f"CCDWorker: failed to emit frame: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"CCDWorker runtime error: {e}", exc_info=True)

        finally:
            # Dừng streaming và disconnect an toàn
            try:
                self._camera_service.stop_streaming()
            except Exception:
                pass

            try:
                self._camera_service.disconnect()
            except Exception:
                pass

            try:
                self._camera_service.cleanup()
            except Exception:
                pass

            logger.info("CCDWorker stopped and cleaned up")

    def stop(self):
        """Yêu cầu dừng thread (sẽ thoát vòng lặp trong run)."""
        self._running = False

