"""
QR Processor - Base class for QR code processing
Hỗ trợ nhiều phương pháp tiền xử lý ảnh để cải thiện detection
"""
import cv2
import numpy as np
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QRProcessor:
    """
    QR Processor - Xử lý tiền xử lý ảnh cho QR detection
    Hỗ trợ nhiều phương pháp preprocessing
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.preprocessing_methods = self._load_preprocessing_methods()
        logger.info(f"QRProcessor initialized with {len(self.preprocessing_methods)} preprocessing methods")
    
    def _load_preprocessing_methods(self):
        """Load preprocessing methods từ config"""
        methods = []
        preprocessing_config = self.config.get('detection', {}).get('preprocessing', [])
        
        for method_config in preprocessing_config:
            method_name = method_config.get('method', 'none')
            methods.append({
                'name': method_name,
                'config': method_config
            })
        
        return methods
    
    def preprocess_image(self, image: np.ndarray, method_index: int = 0) -> np.ndarray:
        """
        Tiền xử lý ảnh theo method được chỉ định
        
        Args:
            image: Input image (BGR or Grayscale)
            method_index: Index của preprocessing method (0-based)
        
        Returns:
            Processed image
        """
        if method_index >= len(self.preprocessing_methods):
            logger.warning(f"Method index {method_index} out of range, using original image")
            return image
        
        method = self.preprocessing_methods[method_index]
        method_name = method['name']
        method_config = method['config']
        
        try:
            if method_name == 'none':
                return image
            
            elif method_name == 'adaptive_threshold':
                return self._adaptive_threshold(image, method_config)
            
            elif method_name == 'histogram_equalization':
                return self._histogram_equalization(image)
            
            elif method_name == 'sharpen':
                return self._sharpen(image, method_config)
            
            elif method_name == 'denoise':
                return self._denoise(image, method_config)
            
            else:
                logger.warning(f"Unknown preprocessing method: {method_name}")
                return image
                
        except Exception as e:
            logger.error(f"Error in preprocessing method '{method_name}': {e}")
            return image
    
    def _adaptive_threshold(self, image: np.ndarray, config: Dict) -> np.ndarray:
        """Adaptive thresholding"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        block_size = config.get('block_size', 11)
        c = config.get('c', 2)
        
        # Ensure block_size is odd
        if block_size % 2 == 0:
            block_size += 1
        
        result = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c
        )
        
        return result
    
    def _histogram_equalization(self, image: np.ndarray) -> np.ndarray:
        """Histogram equalization"""
        if len(image.shape) == 3:
            # Convert to YUV, equalize Y channel, convert back
            yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            result = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        else:
            result = cv2.equalizeHist(image)
        
        return result
    
    def _sharpen(self, image: np.ndarray, config: Dict) -> np.ndarray:
        """Sharpen image"""
        kernel_size = config.get('kernel_size', 3)
        
        # Sharpening kernel
        kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ], dtype=np.float32)
        
        result = cv2.filter2D(image, -1, kernel)
        return result
    
    def _denoise(self, image: np.ndarray, config: Dict) -> np.ndarray:
        """Denoise image"""
        h = config.get('h', 10)
        
        if len(image.shape) == 3:
            result = cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)
        else:
            result = cv2.fastNlMeansDenoising(image, None, h, 7, 21)
        
        return result
    
    def get_preprocessing_count(self) -> int:
        """Lấy số lượng preprocessing methods"""
        return len(self.preprocessing_methods)
    
    def get_preprocessing_name(self, index: int) -> str:
        """Lấy tên của preprocessing method"""
        if 0 <= index < len(self.preprocessing_methods):
            return self.preprocessing_methods[index]['name']
        return "unknown"






