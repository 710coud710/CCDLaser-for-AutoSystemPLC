"""
Domain - Capture Result
Kết quả chụp ảnh từ camera
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class CaptureResult:
    """Kết quả chụp ảnh"""
    success: bool
    image: Optional[np.ndarray] = None
    error_message: Optional[str] = None
    timestamp: Optional[float] = None
    width: int = 0
    height: int = 0

