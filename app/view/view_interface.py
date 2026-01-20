"""
View Interface - Contract giữa View và Presenter
Theo MVP: View chỉ biết interface, không biết logic
"""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class IView(ABC):
    """
    Interface mà View phải implement
    Presenter sẽ gọi các method này để update UI
    """
    
    @abstractmethod
    def show_message(self, message: str, message_type: str = "info"):
        """
        Hiển thị message lên UI
        Args:
            message: Nội dung message
            message_type: "info", "warning", "error", "success"
        """
        pass
    
    @abstractmethod
    def update_status(self, status: str):
        """
        Cập nhật trạng thái ứng dụng lên UI
        Args:
            status: Trạng thái (idle, connecting, connected, etc.)
        """
        pass
    
    @abstractmethod
    def display_image(self, image: np.ndarray):
        """
        Hiển thị ảnh lên UI
        Args:
            image: NumPy array chứa ảnh
        """
        pass
    
    @abstractmethod
    def enable_controls(self, enabled: bool):
        """
        Enable/disable các control trên UI
        Args:
            enabled: True để enable, False để disable
        """
        pass
    
    @abstractmethod
    def update_camera_info(self, info: dict):
        """
        Cập nhật thông tin camera lên UI
        Args:
            info: Dictionary chứa thông tin camera
        """
        pass


class IPresenter(ABC):
    """
    Interface mà Presenter phải implement
    View sẽ gọi các method này khi user tương tác
    """
    
    @abstractmethod
    def on_connect_clicked(self):
        """User click nút Connect"""
        pass
    
    @abstractmethod
    def on_disconnect_clicked(self):
        """User click nút Disconnect"""
        pass
    
    @abstractmethod
    def on_start_stream_clicked(self):
        """User click nút Start Stream"""
        pass
    
    @abstractmethod
    def on_stop_stream_clicked(self):
        """User click nút Stop Stream"""
        pass
    
    @abstractmethod
    def on_capture_clicked(self):
        """User click nút Capture"""
        pass
    
    @abstractmethod
    def on_view_ready(self):
        """View đã sẵn sàng"""
        pass
    
    @abstractmethod
    def on_view_closing(self):
        """View sắp đóng"""
        pass
    
    @abstractmethod
    def on_gain_changed(self, gain_value: int):
        """User thay đổi gain slider"""
        pass
    
    @abstractmethod
    def on_qr_enabled_changed(self, enabled: bool):
        """User thay đổi QR detection enable/disable"""
        pass

    @abstractmethod
    def on_manual_start_clicked(self):
        """User click nút Manual Start (capture từ camera và xử lý với template)"""
        pass

