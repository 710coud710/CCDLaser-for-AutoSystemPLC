"""
Camera Connection Service - Multi-Camera Manager
Quản lý kết nối và điều khiển camera (MindVision hoặc MVS)
"""
import logging
from typing import Optional, Dict, Any
import numpy as np
import cv2
from .camera_base import CameraBase
from .mindvision_camera import MindVisionCamera
from .mvs_camera import MVSCamera

logger = logging.getLogger(__name__)


class CameraConnectionService:
    """
    Service quản lý camera connection (hỗ trợ nhiều loại camera)
    - Tạo và quản lý camera instance
    - Unified interface cho Presenter
    - Hỗ trợ: MindVision (mvsdk) và MVS (Hikvision)
    """
    
    def __init__(self):
        self._camera: Optional[CameraBase] = None
        logger.info("CameraConnectionService initialized")
    
    def create_camera(self, camera_id: str, config: Dict[str, Any]) -> bool:
        """
        Tạo camera instance dựa trên camera_type trong config
        Args:
            camera_id: Camera ID ("cam0", "cam1", "cam2", hoặc SN)
            config: Camera configuration từ YAML
                - camera_type: "mindvision" hoặc "mvs" (default: "mindvision")
        Returns:
            True nếu tạo thành công
        """
        try:
            # Get camera type from config (default: mindvision)
            camera_type = config.get('camera_type', 'mindvision').lower()
            
            logger.info(f"Creating {camera_type} camera: id={camera_id}")
            
            # Cleanup existing camera nếu có
            if self._camera is not None:
                self.cleanup()
            
            # Create camera instance based on type
            if camera_type == 'mvs':
                self._camera = MVSCamera(camera_id, config)
                logger.info("MVS camera instance created (Hikvision SDK)")
            elif camera_type == 'mindvision':
                self._camera = MindVisionCamera(camera_id, config)
                logger.info("MindVision camera instance created (mvsdk)")
            else:
                logger.error(f"Unknown camera type: {camera_type}")
                logger.error("Supported types: 'mindvision', 'mvs'")
                return False
            
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
            frame = self._camera.capture_frame(timeout_ms)
            if frame is None:
                return None

            # Optional flip horizontally (mirror) once for camera frames
            try:
                if bool(getattr(self._camera, "config", {}).get("flip_horizontal", False)):
                    frame = cv2.flip(frame, 1)
            except Exception as flip_err:
                logger.warning(f"Failed to flip frame: {flip_err}")

            return frame
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

    def get_parameter_range(self, param_name: str) -> Optional[tuple]:
        """Lấy min/max tham số nếu camera hỗ trợ."""
        if self._camera is None:
            return None
        try:
            return self._camera.get_parameter_range(param_name)
        except Exception as e:
            logger.error(f"Failed to get parameter range: {e}")
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

