"""
Camera Connection Service - MindVision Camera Manager
Quản lý kết nối và điều khiển MindVision camera
"""
import logging
from typing import Optional, Dict, Any
import numpy as np
from .camera_base import CameraBase
from .mindvision_camera import MindVisionCamera

logger = logging.getLogger(__name__)


class CameraConnectionService:
    """
    Service quản lý MindVision camera connection
    - Tạo và quản lý camera instance
    - Unified interface cho Presenter
    """
    
    def __init__(self):
        self._camera: Optional[CameraBase] = None
        logger.info("CameraConnectionService initialized")
    
    def create_camera(self, camera_id: str, config: Dict[str, Any]) -> bool:
        """
        Tạo MindVision camera instance
        Args:
            camera_id: Camera ID ("cam0", "cam1", "cam2", hoặc SN)
            config: Camera configuration từ YAML
        Returns:
            True nếu tạo thành công
        """
        try:
            logger.info(f"Creating MindVision camera: id={camera_id}")
            
            # Cleanup existing camera nếu có
            if self._camera is not None:
                self.cleanup()
            
            # Tạo MindVision camera instance
            self._camera = MindVisionCamera(camera_id, config)
            logger.info(f"Camera instance created: {self._camera.__class__.__name__}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create camera: {e}", exc_info=True)
            return False
    
    def connect(self) -> bool:
        if self._camera is None:
            logger.error("Cannot connect: no camera instance")
            return False
        
        try:
            logger.info("Connecting to camera...")
            return self._camera.connect()
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            return False
    
    def disconnect(self) -> bool:
        if self._camera is None:
            return True
        
        try:
            logger.info("Disconnecting camera...")
            return self._camera.disconnect()
        except Exception as e:
            logger.error(f"Disconnect failed: {e}", exc_info=True)
            return False
    
    def start_streaming(self) -> bool:
        """
        Bắt đầu streaming (grabbing)
        Returns:
            True nếu thành công
        """
        if self._camera is None:
            logger.error("Cannot start streaming: no camera instance")
            return False
        
        try:
            logger.info("Starting streaming...")
            return self._camera.start_grabbing()
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}", exc_info=True)
            return False
    
    def stop_streaming(self) -> bool:
        """
        Dừng streaming
        Returns:
            True nếu thành công
        """
        if self._camera is None:
            return True
        
        try:
            logger.info("Stopping streaming...")
            return self._camera.stop_grabbing()
        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}", exc_info=True)
            return False
    
    def get_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
        """
        Lấy một frame từ camera
        Args:
            timeout_ms: Timeout tính bằng milliseconds
        Returns:
            NumPy array chứa ảnh, hoặc None nếu thất bại
        """
        if self._camera is None:
            logger.error("Cannot get frame: no camera instance")
            return None
        
        try:
            return self._camera.capture_frame(timeout_ms)
        except Exception as e:
            logger.error(f"Failed to get frame: {e}")
            return None
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """
        Thiết lập tham số camera
        Args:
            param_name: Tên tham số
            value: Giá trị
        Returns:
            True nếu thành công
        """
        if self._camera is None:
            return False
        
        try:
            return self._camera.set_parameter(param_name, value)
        except Exception as e:
            logger.error(f"Failed to set parameter: {e}")
            return False
    
    def get_parameter(self, param_name: str) -> Optional[Any]:
        """
        Lấy giá trị tham số camera
        Args:
            param_name: Tên tham số
        Returns:
            Giá trị tham số hoặc None
        """
        if self._camera is None:
            return None
        
        try:
            return self._camera.get_parameter(param_name)
        except Exception as e:
            logger.error(f"Failed to get parameter: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Kiểm tra camera đã kết nối chưa"""
        if self._camera is None:
            return False
        return self._camera.is_connected
    
    def is_streaming(self) -> bool:
        """Kiểm tra camera đang streaming không"""
        if self._camera is None:
            return False
        return self._camera.is_grabbing
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin camera
        Returns:
            Dictionary chứa thông tin camera
        """
        if self._camera is None:
            return {
                'type': 'None',
                'camera_id': '',
                'is_connected': False,
                'is_grabbing': False
            }
        
        return self._camera.get_info()
    
    def cleanup(self):
        """
        Cleanup resources - gọi trước khi thoát app
        Đảm bảo camera được disconnect đúng cách
        """
        logger.info("Cleaning up camera resources...")
        
        if self._camera is not None:
            try:
                self._camera.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            finally:
                self._camera = None
        
        logger.info("Camera cleanup completed")

