"""
State Machine - Quản lý trạng thái ứng dụng
Đảm bảo các transition hợp lệ giữa các state
"""
import logging
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class AppState(Enum):
    """Các trạng thái của ứng dụng"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    RUNNING = "running"    # Running mode - chạy với template đã chọn
    ERROR = "error"


class StateMachine:
    """
    State Machine quản lý luồng trạng thái
    Đảm bảo chỉ cho phép các transition hợp lệ
    """
    
    # Định nghĩa các transition hợp lệ
    VALID_TRANSITIONS = {
        AppState.IDLE: [AppState.CONNECTING],
        AppState.CONNECTING: [AppState.CONNECTED, AppState.ERROR, AppState.IDLE],
        AppState.CONNECTED: [AppState.STREAMING, AppState.RUNNING, AppState.IDLE],
        AppState.STREAMING: [AppState.CONNECTED, AppState.ERROR],
        AppState.RUNNING: [AppState.CONNECTED, AppState.ERROR],
        AppState.ERROR: [AppState.IDLE]
    }
    
    def __init__(self):
        self._current_state = AppState.IDLE
        self._state_change_callback: Optional[Callable] = None
        logger.info("StateMachine initialized")
    
    def set_state_change_callback(self, callback: Callable):
        """
        Đăng ký callback khi state thay đổi
        Args:
            callback: Function nhận (old_state, new_state)
        """
        self._state_change_callback = callback
    
    @property
    def current_state(self) -> AppState:
        """Lấy state hiện tại"""
        return self._current_state
    
    def can_transition_to(self, new_state: AppState) -> bool:
        """
        Kiểm tra có thể chuyển sang state mới không
        Args:
            new_state: State muốn chuyển đến
        Returns:
            True nếu transition hợp lệ
        """
        valid_states = self.VALID_TRANSITIONS.get(self._current_state, [])
        return new_state in valid_states
    
    def transition_to(self, new_state: AppState) -> bool:
        """
        Chuyển sang state mới
        Args:
            new_state: State muốn chuyển đến
        Returns:
            True nếu chuyển thành công
        """
        if not self.can_transition_to(new_state):
            logger.warning(
                f"Invalid transition: {self._current_state.value} -> {new_state.value}"
            )
            return False
        
        old_state = self._current_state
        self._current_state = new_state
        
        logger.info(f"State transition: {old_state.value} -> {new_state.value}")
        
        # Trigger callback
        if self._state_change_callback:
            try:
                self._state_change_callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}", exc_info=True)
        
        return True
    
    def reset(self):
        """Reset về IDLE state"""
        logger.info("Resetting state machine to IDLE")
        old_state = self._current_state
        self._current_state = AppState.IDLE
        
        if self._state_change_callback:
            try:
                self._state_change_callback(old_state, AppState.IDLE)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}", exc_info=True)
    
    def is_idle(self) -> bool:
        """Kiểm tra có đang ở IDLE không"""
        return self._current_state == AppState.IDLE
    
    def is_connected(self) -> bool:
        """Kiểm tra có đang connected không"""
        return self._current_state in [AppState.CONNECTED, AppState.STREAMING]
    
    def is_streaming(self) -> bool:
        """Kiểm tra có đang streaming không"""
        return self._current_state == AppState.STREAMING
    
    def is_running(self) -> bool:
        """Kiểm tra có đang ở Running mode không"""
        return self._current_state == AppState.RUNNING

