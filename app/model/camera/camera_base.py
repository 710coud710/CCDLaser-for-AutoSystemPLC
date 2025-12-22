"""
Camera Base - Interface cho tất cả camera
Theo nguyên tắc: Presenter không biết camera là MindVision hay hãng khác
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import numpy as np


class CameraBase(ABC):
    """
    Base class cho tất cả camera
    Định nghĩa interface chung mà mọi camera phải implement
    """
    
    def __init__(self, camera_id: str, config: Dict[str, Any]):
        """
        Args:
            camera_id: ID định danh camera (IP, Serial Number, etc.)
            config: Cấu hình camera từ YAML
        """
        self.camera_id = camera_id
        self.config = config
        self._is_connected = False
        self._is_grabbing = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Kết nối đến camera
        Returns:
            True nếu kết nối thành công, False nếu thất bại
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Ngắt kết nối camera
        Returns:
            True nếu ngắt kết nối thành công
        """
        pass
    
    @abstractmethod
    def start_grabbing(self) -> bool:
        """
        Bắt đầu chế độ lấy ảnh (streaming)
        Returns:
            True nếu thành công
        """
        pass
    
    @abstractmethod
    def stop_grabbing(self) -> bool:
        """
        Dừng chế độ lấy ảnh
        Returns:
            True nếu thành công
        """
        pass
    
    @abstractmethod
    def capture_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
        """
        Chụp một frame
        Args:
            timeout_ms: Timeout tính bằng milliseconds
        Returns:
            NumPy array chứa ảnh, hoặc None nếu thất bại
        """
        pass
    
    @abstractmethod
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """
        Thiết lập tham số camera
        Args:
            param_name: Tên tham số
            value: Giá trị
        Returns:
            True nếu thiết lập thành công
        """
        pass
    
    @abstractmethod
    def get_parameter(self, param_name: str) -> Optional[Any]:
        """
        Lấy giá trị tham số camera
        Args:
            param_name: Tên tham số
        Returns:
            Giá trị tham số hoặc None
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """Kiểm tra camera đã kết nối chưa"""
        return self._is_connected
    
    @property
    def is_grabbing(self) -> bool:
        """Kiểm tra camera đang grab không"""
        return self._is_grabbing
    
    def get_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin camera
        Returns:
            Dictionary chứa thông tin camera
        """
        return {
            'camera_id': self.camera_id,
            'is_connected': self._is_connected,
            'is_grabbing': self._is_grabbing
        }

