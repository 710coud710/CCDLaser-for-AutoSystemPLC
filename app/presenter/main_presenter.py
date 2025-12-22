"""
Main Presenter - Điều phối giữa View và Model
Theo MVP: Presenter chứa logic, không biết chi tiết UI
"""
import logging
from typing import Optional
from PySide6.QtCore import QObject, QTimer
from app.view.view_interface import IView, IPresenter
from app.model.camera import CameraBase
from .state_machine import StateMachine, AppState

logger = logging.getLogger(__name__)


class MainPresenter(QObject):
    """
    Main Presenter
    - Điều phối giữa View và Model
    - Quản lý state machine
    - Xử lý business logic
    """
    
    def __init__(self, view: IView, config: dict):
        super().__init__()
        self._view = view
        self._config = config
        
        # Model
        self._camera_service = CameraBase()
        
        # State machine
        self._state_machine = StateMachine()
        self._state_machine.set_state_change_callback(self._on_state_changed)
        
        # Timer cho streaming
        self._stream_timer = QTimer()
        self._stream_timer.timeout.connect(self._on_stream_timer)
        self._stream_interval = 33  # ~30 FPS
        
        logger.info("MainPresenter initialized")
    
    # ========== IPresenter Implementation ==========
    
    def on_view_ready(self):
        """View đã sẵn sàng"""
        logger.info("View ready")
        self._view.update_status("idle")
        self._view.show_message("Application ready", "info")
    
    def on_view_closing(self):
        """View sắp đóng - cleanup"""
        logger.info("View closing - cleaning up...")
        
        # Stop streaming nếu đang chạy
        if self._state_machine.is_streaming():
            self._stop_streaming()
        
        # Disconnect camera nếu đang connected
        if self._state_machine.is_connected():
            self._disconnect_camera()
        
        # Cleanup
        self._camera_service.cleanup()
        logger.info("Cleanup completed")
    
    def on_connect_clicked(self):
        """User click Connect"""
        logger.info("Connect button clicked")
        
        if not self._state_machine.can_transition_to(AppState.CONNECTING):
            self._view.show_message("Cannot connect in current state", "warning")
            return
        
        self._connect_camera()
    
    def on_disconnect_clicked(self):
        """User click Disconnect"""
        logger.info("Disconnect button clicked")
        
        # Stop streaming trước nếu đang stream
        if self._state_machine.is_streaming():
            self._stop_streaming()
        
        self._disconnect_camera()
    
    def on_start_stream_clicked(self):
        """User click Start Stream"""
        logger.info("Start stream button clicked")
        
        if not self._state_machine.can_transition_to(AppState.STREAMING):
            self._view.show_message("Cannot start streaming in current state", "warning")
            return
        
        self._start_streaming()
    
    def on_stop_stream_clicked(self):
        """User click Stop Stream"""
        logger.info("Stop stream button clicked")
        self._stop_streaming()
    
    def on_capture_clicked(self):
        """User click Capture"""
        logger.info("Capture button clicked")
        self._capture_single_frame()
    
    # ========== Private Methods ==========
    
    def _connect_camera(self):
        """Kết nối camera"""
        try:
            # Transition to CONNECTING
            if not self._state_machine.transition_to(AppState.CONNECTING):
                return
            
            self._view.update_status("connecting")
            self._view.show_message("Connecting to camera...", "info")
            
            # Lấy config từ YAML
            camera_config = self._config.get('camera', {})
            camera_type = camera_config.get('type', 'mock')
            camera_id = camera_config.get('ip', '192.168.1.41')
            
            logger.info(f"Connecting to {camera_type} camera at {camera_id}")
            
            # Tạo camera instance
            if not self._camera_service.create_camera(camera_type, camera_id, camera_config):
                raise Exception("Failed to create camera instance")
            
            # Connect
            if not self._camera_service.connect():
                raise Exception("Failed to connect to camera")
            
            # Transition to CONNECTED
            self._state_machine.transition_to(AppState.CONNECTED)
            
            # Update view
            camera_info = self._camera_service.get_camera_info()
            self._view.update_camera_info(camera_info)
            self._view.show_message("Camera connected successfully", "success")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._state_machine.transition_to(AppState.ERROR)
            self._view.show_message(f"Connection failed: {e}", "error")
            self._state_machine.reset()
    
    def _disconnect_camera(self):
        """Ngắt kết nối camera"""
        try:
            logger.info("Disconnecting camera...")
            
            # Disconnect
            self._camera_service.disconnect()
            
            # Reset state
            self._state_machine.reset()
            
            # Update view
            self._view.show_message("Camera disconnected", "info")
            
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            self._view.show_message(f"Disconnect failed: {e}", "error")
    
    def _start_streaming(self):
        """Bắt đầu streaming"""
        try:
            logger.info("Starting streaming...")
            
            # Start grabbing
            if not self._camera_service.start_streaming():
                raise Exception("Failed to start streaming")
            
            # Transition to STREAMING
            if not self._state_machine.transition_to(AppState.STREAMING):
                self._camera_service.stop_streaming()
                return
            
            # Start timer để lấy frame liên tục
            self._stream_timer.start(self._stream_interval)
            
            self._view.show_message("Streaming started", "success")
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            self._view.show_message(f"Failed to start streaming: {e}", "error")
    
    def _stop_streaming(self):
        """Dừng streaming"""
        try:
            logger.info("Stopping streaming...")
            
            # Stop timer
            self._stream_timer.stop()
            
            # Stop grabbing
            self._camera_service.stop_streaming()
            
            # Transition back to CONNECTED
            self._state_machine.transition_to(AppState.CONNECTED)
            
            self._view.show_message("Streaming stopped", "info")
            
        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}")
            self._view.show_message(f"Failed to stop streaming: {e}", "error")
    
    def _on_stream_timer(self):
        """Timer callback - lấy frame và hiển thị"""
        try:
            # Get frame
            frame = self._camera_service.get_frame(timeout_ms=100)
            
            if frame is not None:
                # Display frame
                self._view.display_image(frame)
            else:
                logger.warning("Failed to get frame")
                
        except Exception as e:
            logger.error(f"Error in stream timer: {e}")
            # Không stop streaming ngay, cho phép retry
    
    def _capture_single_frame(self):
        """Chụp một frame đơn"""
        try:
            logger.info("Capturing single frame...")
            
            frame = self._camera_service.get_frame(timeout_ms=1000)
            
            if frame is not None:
                self._view.display_image(frame)
                self._view.show_message("Frame captured", "success")
            else:
                self._view.show_message("Failed to capture frame", "error")
                
        except Exception as e:
            logger.error(f"Capture failed: {e}")
            self._view.show_message(f"Capture failed: {e}", "error")
    
    def _on_state_changed(self, old_state: AppState, new_state: AppState):
        """Callback khi state thay đổi"""
        logger.info(f"State changed: {old_state.value} -> {new_state.value}")
        
        # Update view based on new state
        self._view.update_status(new_state.value)
        
        # Update camera info
        if self._camera_service.is_connected():
            camera_info = self._camera_service.get_camera_info()
            self._view.update_camera_info(camera_info)

