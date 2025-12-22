"""
Domain - App Status
Định nghĩa các trạng thái của ứng dụng
"""
from enum import Enum


class AppStatus(Enum):
    """Trạng thái của ứng dụng"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    ERROR = "error"
    DISCONNECTED = "disconnected"

