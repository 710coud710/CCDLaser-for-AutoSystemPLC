"""
Mock Camera - Camera giả để test khi không có hardware
Tạo ảnh test với pattern hoặc từ file
"""
import numpy as np
from typing import Optional, Dict, Any
from .camera_base import CameraBase
import logging
import time

logger = logging.getLogger(__name__)


class MockCamera(CameraBase):
    """
    Mock Camera để test
    - Tạo ảnh pattern động
    - Simulate delay giống camera thật
    - Không cần hardware
    """
    
    def __init__(self, camera_id: str, config: Dict[str, Any]):
        super().__init__(camera_id, config)
        self._frame_counter = 0
        self._width = config.get('width', 1280)
        self._height = config.get('height', 1024)
        self._pixel_format = config.get('pixel_format', 'Mono8')
        logger.info(f"MockCamera created: {camera_id}")
    
    def connect(self) -> bool:
        """Giả lập kết nối camera"""
        try:
            logger.info(f"Connecting to mock camera: {self.camera_id}")
            
            # Simulate connection delay
            time.sleep(0.5)
            
            self._is_connected = True
            logger.info("Mock camera connected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect mock camera: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Giả lập ngắt kết nối"""
        try:
            logger.info(f"Disconnecting mock camera: {self.camera_id}")
            
            if self._is_grabbing:
                self.stop_grabbing()
            
            self._is_connected = False
            logger.info("Mock camera disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect mock camera: {e}")
            return False
    
    def start_grabbing(self) -> bool:
        """Bắt đầu grabbing"""
        if not self._is_connected:
            logger.error("Cannot start grabbing: not connected")
            return False
        
        try:
            logger.info("Starting grabbing on mock camera")
            self._is_grabbing = True
            self._frame_counter = 0
            return True
            
        except Exception as e:
            logger.error(f"Failed to start grabbing: {e}")
            return False
    
    def stop_grabbing(self) -> bool:
        """Dừng grabbing"""
        if not self._is_grabbing:
            return True
        
        try:
            logger.info("Stopping grabbing on mock camera")
            self._is_grabbing = False
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop grabbing: {e}")
            return False
    
    def capture_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
        if not self._is_connected or not self._is_grabbing:
            logger.error("Cannot capture: camera not ready")
            return None
        
        try:
            time.sleep(0.01)  # 10ms delay giống camera thật
            
            # Generate test image
            image = self._generate_test_image()
            
            self._frame_counter += 1
            
            return image
            
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return None
    
    def _generate_test_image(self) -> np.ndarray:
        """
        Tạo test image với pattern động
        - Moving gradient
        - Frame counter text
        """
        # Create base image
        if self._pixel_format == 'Mono8':
            # Grayscale image with moving pattern
            x = np.linspace(0, 255, self._width)
            y = np.linspace(0, 255, self._height)
            xx, yy = np.meshgrid(x, y)
            
            # Create moving pattern
            offset = (self._frame_counter * 2) % 256
            image = np.clip((xx + yy + offset) % 256, 0, 255).astype(np.uint8)
            
        else:  # RGB
            # Color image with moving pattern
            image = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            
            # Red channel
            offset_r = (self._frame_counter * 2) % 256
            x = np.linspace(0, 255, self._width)
            y = np.linspace(0, 255, self._height)
            xx, yy = np.meshgrid(x, y)
            image[:, :, 0] = np.clip((xx + offset_r) % 256, 0, 255).astype(np.uint8)
            
            # Green channel
            offset_g = (self._frame_counter * 3) % 256
            image[:, :, 1] = np.clip((yy + offset_g) % 256, 0, 255).astype(np.uint8)
            
            # Blue channel
            offset_b = (self._frame_counter * 5) % 256
            image[:, :, 2] = np.clip((xx + yy + offset_b) % 256, 0, 255).astype(np.uint8)
        
        # Add frame counter text (simple)
        # Draw a white rectangle in top-left corner
        text_height = 30
        text_width = 200
        if len(image.shape) == 2:  # Grayscale
            image[0:text_height, 0:text_width] = 255
            # Draw some "text" pattern
            image[5:25, 5:195] = (self._frame_counter % 256)
        else:  # Color
            image[0:text_height, 0:text_width, :] = [255, 255, 255]
            image[5:25, 5:195, :] = [0, 255, 0]  # Green for frame counter
        
        return image
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """Set parameter (mock - chỉ log)"""
        logger.info(f"MockCamera: Setting {param_name} = {value}")
        
        # Store in config for reference
        self.config[param_name.lower()] = value
        
        return True
    
    def get_parameter(self, param_name: str) -> Optional[Any]:
        """Get parameter (mock)"""
        return self.config.get(param_name.lower())
    
    def get_info(self) -> Dict[str, Any]:
        """Get camera info"""
        info = super().get_info()
        info.update({
            'type': 'MockCamera',
            'width': self._width,
            'height': self._height,
            'pixel_format': self._pixel_format,
            'frame_count': self._frame_counter
        })
        return info

