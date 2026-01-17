"""
QR Detection Service - Detect QR codes in images with ROI support
Hỗ trợ nhiều vùng ROI và nhiều lần xử lý
"""
import cv2
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import logging
import os
from datetime import datetime

from .qr_processor import QRProcessor

logger = logging.getLogger(__name__)


@dataclass
class ROIRegion:
    """ROI Region definition"""
    name: str
    enabled: bool
    x: int
    y: int
    width: int
    height: int
    use_percentage: bool
    
    def get_absolute_coords(self, image_width: int, image_height: int) -> Tuple[int, int, int, int]:
        """Convert to absolute coordinates"""
        if self.use_percentage:
            x = int(self.x * image_width)
            y = int(self.y * image_height)
            w = int(self.width * image_width)
            h = int(self.height * image_height)
        else:
            x, y, w, h = self.x, self.y, self.width, self.height
        
        # Clamp to image bounds
        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        w = max(1, min(w, image_width - x))
        h = max(1, min(h, image_height - y))
        
        return x, y, w, h


@dataclass
class QRDetectionResult:
    """QR Detection result"""
    success: bool
    data: str
    roi_name: str
    attempt: int
    preprocessing_method: str
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) in ROI coordinates
    polygon: Optional[List[Tuple[int, int]]] = None  # Polygon points in ROI coordinates
    confidence: float = 0.0
    
    def get_absolute_bbox(self, roi_x: int, roi_y: int) -> Optional[Tuple[int, int, int, int]]:
        """Get bounding box in absolute image coordinates"""
        if self.bbox is None:
            return None
        x, y, w, h = self.bbox
        return (x + roi_x, y + roi_y, w, h)
    
    def get_absolute_polygon(self, roi_x: int, roi_y: int) -> Optional[List[Tuple[int, int]]]:
        """Get polygon in absolute image coordinates"""
        if self.polygon is None:
            return None
        return [(x + roi_x, y + roi_y) for x, y in self.polygon]


class QRDetectionService:
    """
    QR Detection Service
    - Detect QR codes trong nhiều ROI regions
    - Hỗ trợ nhiều lần xử lý với preprocessing khác nhau
    - Validation và visualization
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        
        # Load ROI regions
        self.roi_regions = self._load_roi_regions()
        
        # QR Processor
        self.processor = QRProcessor(config)
        
        # Detection settings
        detection_config = config.get('detection', {})
        self.max_attempts = detection_config.get('max_attempts', 3)
        
        # Validation settings
        validation_config = config.get('validation', {})
        self.min_length = validation_config.get('min_length', 1)
        self.max_length = validation_config.get('max_length', 0)
        self.pattern = validation_config.get('pattern', '')
        self.required_prefix = validation_config.get('required_prefix', '')
        self.required_suffix = validation_config.get('required_suffix', '')
        
        # Visualization settings
        vis_config = config.get('visualization', {})
        self.draw_roi = vis_config.get('draw_roi', True)
        self.roi_color = tuple(vis_config.get('roi_color', [0, 255, 0]))
        self.roi_thickness = vis_config.get('roi_thickness', 2)
        self.draw_qr = vis_config.get('draw_qr', True)
        self.qr_color = tuple(vis_config.get('qr_color', [255, 0, 0]))
        self.qr_thickness = vis_config.get('qr_thickness', 2)
        self.draw_text = vis_config.get('draw_text', True)
        self.text_color = tuple(vis_config.get('text_color', [0, 255, 255]))
        self.text_size = vis_config.get('text_size', 0.6)
        self.text_thickness = vis_config.get('text_thickness', 2)
        
        # Logging settings
        log_config = config.get('logging', {})
        self.log_results = log_config.get('log_results', True)
        self.log_failures = log_config.get('log_failures', False)
        self.save_debug_images = log_config.get('save_debug_images', False)
        self.debug_image_path = log_config.get('debug_image_path', 'logs/qr_debug')
        
        if self.save_debug_images:
            os.makedirs(self.debug_image_path, exist_ok=True)
        
        logger.info(f"QRDetectionService initialized: {len(self.roi_regions)} ROI regions, max_attempts={self.max_attempts}")
    
    def _load_roi_regions(self) -> List[ROIRegion]:
        """Load ROI regions từ config"""
        regions = []
        roi_configs = self.config.get('roi_regions', [])
        
        for roi_config in roi_configs:
            region = ROIRegion(
                name=roi_config.get('name', 'Unknown'),
                enabled=roi_config.get('enabled', True),
                x=roi_config.get('x', 0),
                y=roi_config.get('y', 0),
                width=roi_config.get('width', 100),
                height=roi_config.get('height', 100),
                use_percentage=roi_config.get('use_percentage', False)
            )
            regions.append(region)
            logger.info(f"ROI Region loaded: {region.name} ({'enabled' if region.enabled else 'disabled'})")
        
        return regions
    
    def detect_qr_codes(self, image: np.ndarray) -> List[QRDetectionResult]:
        """
        Detect QR codes trong image
        
        Args:
            image: Input image (BGR)
        
        Returns:
            List of QRDetectionResult
        """
        if not self.enabled:
            return []
        
        results = []
        image_height, image_width = image.shape[:2]
        
        # Process each ROI region
        for roi_region in self.roi_regions:
            if not roi_region.enabled:
                continue
            
            # Get ROI coordinates
            roi_x, roi_y, roi_w, roi_h = roi_region.get_absolute_coords(image_width, image_height)
            
            # Extract ROI
            roi_image = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w].copy()
            
            # Try detection with multiple preprocessing methods
            for attempt in range(min(self.max_attempts, self.processor.get_preprocessing_count())):
                # Preprocess image
                processed_image = self.processor.preprocess_image(roi_image, attempt)
                preprocessing_method = self.processor.get_preprocessing_name(attempt)
                
                # Detect QR codes using OpenCV
                qr_detector = cv2.QRCodeDetector()
                retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(processed_image)
                
                if retval and decoded_info:
                    for i, data in enumerate(decoded_info):
                        if not data:  # Skip empty data
                            continue
                        
                        # Validate
                        if not self._validate_qr_data(data):
                            if self.log_failures:
                                logger.warning(f"QR validation failed in {roi_region.name}: {data}")
                            continue
                        
                        # Extract bounding box and polygon from points
                        if points is not None and len(points) > i:
                            point_set = points[i]
                            if point_set is not None and len(point_set) > 0:
                                # Convert points to bbox
                                xs = [p[0] for p in point_set]
                                ys = [p[1] for p in point_set]
                                bbox = (int(min(xs)), int(min(ys)), 
                                        int(max(xs) - min(xs)), int(max(ys) - min(ys)))
                                
                                # Polygon is the points themselves
                                polygon = [(int(p[0]), int(p[1])) for p in point_set]
                            else:
                                bbox = (0, 0, 0, 0)
                                polygon = []
                        else:
                            bbox = (0, 0, 0, 0)
                            polygon = []
                        
                        # Create result
                        result = QRDetectionResult(
                            success=True,
                            data=data,
                            roi_name=roi_region.name,
                            attempt=attempt,
                            preprocessing_method=preprocessing_method,
                            bbox=bbox,
                            polygon=polygon,
                            confidence=1.0  # OpenCV doesn't provide confidence
                        )
                        
                        results.append(result)
                        
                        if self.log_results:
                            logger.info(f"QR detected in {roi_region.name} (attempt {attempt}, method: {preprocessing_method}): {data}")
                        
                        # Found QR in this ROI, break attempt loop
                        break
                
                # If found QR, break attempt loop
                if results and results[-1].roi_name == roi_region.name:
                    break
            
            # Log if no QR found in this ROI
            if self.log_failures and (not results or results[-1].roi_name != roi_region.name):
                logger.warning(f"No QR code found in {roi_region.name} after {self.max_attempts} attempts")
        
        return results
    
    def _validate_qr_data(self, data: str) -> bool:
        """Validate QR data"""
        # Check length
        if len(data) < self.min_length:
            return False
        
        if self.max_length > 0 and len(data) > self.max_length:
            return False
        
        # Check prefix
        if self.required_prefix and not data.startswith(self.required_prefix):
            return False
        
        # Check suffix
        if self.required_suffix and not data.endswith(self.required_suffix):
            return False
        
        # Check pattern (regex)
        if self.pattern:
            import re
            if not re.match(self.pattern, data):
                return False
        
        return True
    
    def draw_results(self, image: np.ndarray, results: List[QRDetectionResult]) -> np.ndarray:
        """
        Draw detection results on image
        
        Args:
            image: Input image (BGR)
            results: Detection results
        
        Returns:
            Image with drawings
        """
        output = image.copy()
        image_height, image_width = output.shape[:2]
        
        # Draw ROI regions
        if self.draw_roi:
            for roi_region in self.roi_regions:
                if not roi_region.enabled:
                    continue
                
                roi_x, roi_y, roi_w, roi_h = roi_region.get_absolute_coords(image_width, image_height)
                cv2.rectangle(output, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), 
                            self.roi_color, self.roi_thickness)
                
                # Draw ROI name
                cv2.putText(output, roi_region.name, (roi_x, roi_y - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, self.text_size, self.roi_color, self.text_thickness)
        
        # Draw QR detection results
        if self.draw_qr:
            for result in results:
                # Find ROI region
                roi_region = next((r for r in self.roi_regions if r.name == result.roi_name), None)
                if roi_region is None:
                    continue
                
                roi_x, roi_y, roi_w, roi_h = roi_region.get_absolute_coords(image_width, image_height)
                
                # Draw polygon
                if result.polygon:
                    abs_polygon = result.get_absolute_polygon(roi_x, roi_y)
                    if abs_polygon:
                        points = np.array(abs_polygon, dtype=np.int32)
                        cv2.polylines(output, [points], True, self.qr_color, self.qr_thickness)
                
                # Draw bounding box
                if result.bbox:
                    abs_bbox = result.get_absolute_bbox(roi_x, roi_y)
                    if abs_bbox:
                        x, y, w, h = abs_bbox
                        cv2.rectangle(output, (x, y), (x + w, y + h), self.qr_color, self.qr_thickness)
                
                # Draw text
                if self.draw_text and result.bbox:
                    abs_bbox = result.get_absolute_bbox(roi_x, roi_y)
                    if abs_bbox:
                        x, y, w, h = abs_bbox
                        text = f"{result.data}"
                        cv2.putText(output, text, (x, y - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, self.text_size, self.text_color, self.text_thickness)
        
        return output
    
    def save_debug_image(self, image: np.ndarray, results: List[QRDetectionResult]):
        """Save debug image with detection results"""
        if not self.save_debug_images:
            return
        
        try:
            # Draw results
            output = self.draw_results(image, results)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"qr_debug_{timestamp}.jpg"
            filepath = os.path.join(self.debug_image_path, filename)
            
            # Save
            cv2.imwrite(filepath, output)
            logger.info(f"Debug image saved: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save debug image: {e}")
    
    def update_roi_region(self, roi_name: str, x: int, y: int, width: int, height: int, 
                         use_percentage: bool = False):
        """Update ROI region coordinates"""
        for roi_region in self.roi_regions:
            if roi_region.name == roi_name:
                roi_region.x = x
                roi_region.y = y
                roi_region.width = width
                roi_region.height = height
                roi_region.use_percentage = use_percentage
                logger.info(f"ROI region updated: {roi_name}")
                return True
        
        logger.warning(f"ROI region not found: {roi_name}")
        return False
    
    def enable_roi_region(self, roi_name: str, enabled: bool = True):
        """Enable/disable ROI region"""
        for roi_region in self.roi_regions:
            if roi_region.name == roi_name:
                roi_region.enabled = enabled
                logger.info(f"ROI region {roi_name}: {'enabled' if enabled else 'disabled'}")
                return True
        
        logger.warning(f"ROI region not found: {roi_name}")
        return False
    
    def get_roi_regions(self) -> List[ROIRegion]:
        """Get all ROI regions"""
        return self.roi_regions.copy()


