import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
import numpy as np
import cv2

# Try to import pylibdmtx for DataMatrix support
try:
    from pylibdmtx.pylibdmtx import decode as dmtx_decode
    DMTX_AVAILABLE = True
except ImportError:
    DMTX_AVAILABLE = False
    logging.warning("pylibdmtx not available - DataMatrix detection disabled")

# Try to import pyzbar for better barcode/QR detection
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logging.warning("pyzbar not available - pyzbar detection disabled")

from .template_model import Template, CropRegion

logger = logging.getLogger(__name__)


class TemplateService:
    """
    Service quản lý templates
    - Lưu templates vào AppData
    - Load/List templates
    - Process images với template
    - Scan barcodes
    """
    
    def __init__(self):
        # Get AppData path
        self.templates_dir = self._get_templates_directory()
        
        # Create directory if not exists
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Current template
        self._current_template: Optional[Template] = None
        
        # Log directory for processed images
        self.logccd_dir = self._get_logccd_directory()
        os.makedirs(self.logccd_dir, exist_ok=True)
        
        logger.info(f"TemplateService initialized, templates dir: {self.templates_dir}")
        logger.info(f"LogCCD directory: {self.logccd_dir}")
    
    def _get_logccd_directory(self) -> str:
        """Get logccd directory for saving processed images"""
        from services.appPathService import getAppDirectory
        base_path = getAppDirectory()
        logccd_dir = os.path.join(base_path, "logccd")
        return logccd_dir
    
    def _get_templates_directory(self) -> str:
        """Get templates directory in AppData"""
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            if appdata:
                templates_dir = os.path.join(appdata, 'CCDLaser', 'templates')
            else:
                # Fallback
                templates_dir = os.path.join(os.path.expanduser('~'), 'CCDLaser', 'templates')
        else:  # Linux/Mac
            templates_dir = os.path.join(os.path.expanduser('~'), '.ccdlaser', 'templates')
        
        return templates_dir
    
    def save_template(self, template: Template) -> bool:
        """
        Save template to AppData
        
        Args:
            template: Template to save
        
        Returns:
            True if successful
        """
        try:
            # Create filename
            filename = f"{template.name}.json"
            filepath = os.path.join(self.templates_dir, filename)
            
            # Update timestamp
            from datetime import datetime
            template.updated_at = datetime.now().isoformat()
            
            # Save to JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template.to_json())
            
            logger.info(f"Template saved: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save template: {e}", exc_info=True)
            return False
    
    def load_template(self, template_name: str) -> Optional[Template]:
        """
        Load template from AppData
        
        Args:
            template_name: Template name (without .json)
        
        Returns:
            Template object or None
        """
        try:
            filename = f"{template_name}.json"
            filepath = os.path.join(self.templates_dir, filename)
            
            if not os.path.exists(filepath):
                logger.warning(f"Template not found: {filepath}")
                return None
            
            # Load from JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            template = Template.from_json(json_str)
            logger.info(f"Template loaded: {template_name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to load template: {e}", exc_info=True)
            return None
    
    def list_templates(self) -> List[str]:
        """
        List all available templates
        
        Returns:
            List of template names
        """
        try:
            if not os.path.exists(self.templates_dir):
                return []
            
            templates = []
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json'):
                    template_name = filename[:-5]  # Remove .json
                    templates.append(template_name)
            
            templates.sort()
            logger.info(f"Found {len(templates)} template(s)")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}", exc_info=True)
            return []
    
    def delete_template(self, template_name: str) -> bool:
        """
        Delete template
        
        Args:
            template_name: Template name
        
        Returns:
            True if successful
        """
        try:
            filename = f"{template_name}.json"
            filepath = os.path.join(self.templates_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Template deleted: {template_name}")
                return True
            else:
                logger.warning(f"Template not found: {template_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete template: {e}", exc_info=True)
            return False
    
    def set_current_template(self, template: Template):
        """Set current template"""
        self._current_template = template
        logger.info(f"Current template set: {template.name}")
    
    def get_current_template(self) -> Optional[Template]:
        """Get current template"""
        return self._current_template
    
    def crop_image_regions(self, image: np.ndarray, template: Template) -> Dict[str, np.ndarray]:
        """
        Crop image regions based on template
        
        Args:
            image: Input image
            template: Template with crop regions
        
        Returns:
            Dictionary of {region_name: cropped_image}
        """
        cropped_images = {}
        
        for region in template.crop_regions:
            if not region.enabled:
                continue
            
            try:
                # Crop region
                x, y, w, h = region.x, region.y, region.width, region.height
                
                # Validate bounds
                img_h, img_w = image.shape[:2]
                x = max(0, min(x, img_w - 1))
                y = max(0, min(y, img_h - 1))
                w = max(1, min(w, img_w - x))
                h = max(1, min(h, img_h - y))
                
                # Crop
                cropped = image[y:y+h, x:x+w].copy()
                cropped_images[region.name] = cropped
                
                logger.debug(f"Cropped region '{region.name}': {w}x{h}")
                
            except Exception as e:
                logger.error(f"Failed to crop region '{region.name}': {e}")
        
        return cropped_images
    
    def _preprocess_for_barcode(self, roi: np.ndarray, method: int) -> np.ndarray:
        # Image is already grayscale (mono mode), no conversion needed
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi.copy()
        
        if method == 0:
            # Original - no processing
            return gray
        
        elif method == 1:
            # CLAHE (Contrast Limited Adaptive Histogram Equalization) + Binarization
            # Tăng tương phản với CLAHE, sau đó nhị phân hóa
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        
        elif method == 2:
            # CLAHE + Light Denoise + Binarization (RECOMMENDED for mono images)
            # Tăng tương phản CLAHE, giảm nhiễu nhẹ, nhị phân hóa
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            # Light denoising (h=10 is light, h=20 is stronger)
            denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        
        elif method == 3:
            # Adaptive threshold (good for varying lighting)
            return cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        
        elif method == 4:
            # Otsu threshold only
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        
        elif method == 5:
            # CLAHE only (no binarization)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            return clahe.apply(gray)
        
        elif method == 6:
            # Denoise + CLAHE + Binarization
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        
        elif method == 7:
            # Invert + CLAHE + Denoise + Binarization (for white-on-dark barcodes)
            # Invert image first (white barcode on dark background -> dark on white)
            inverted = cv2.bitwise_not(gray)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(inverted)
            denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        
        elif method == 8:
            # Invert only (for white-on-dark barcodes)
            return cv2.bitwise_not(gray)
        
        elif method == 9:
            # Testbase method: CLAHE + Median Blur + Adaptive Threshold + Morphology
            # Theo đúng testbase.py
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrast = clahe.apply(gray)
            denoise = cv2.medianBlur(contrast, 3)
            binary = cv2.adaptiveThreshold(
                denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 5
            )
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            return morph
        
        elif method == 10:
            # Testbase method without morphology: CLAHE + Median Blur + Adaptive Threshold
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrast = clahe.apply(gray)
            denoise = cv2.medianBlur(contrast, 3)
            binary = cv2.adaptiveThreshold(
                denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 5
            )
            return binary
        
        elif method == 11:
            # Testbase method: CLAHE only (clipLimit=2.0 như testbase)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray)
        
        return gray
    
    def _detect_qr_opencv(self, roi: np.ndarray) -> List[str]:
        """
        Detect QR code using OpenCV QRCodeDetector
        
        Args:
            roi: Input ROI image
        
        Returns:
            List of QR code data strings
        """
        qr_data_list = []
        
        try:
            # Initialize QRCode detector
            qr_detector = cv2.QRCodeDetector()
            
            # Detect and decode
            retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(roi)
            
            if retval:
                for data in decoded_info:
                    if data and data not in qr_data_list:
                        qr_data_list.append(data)
                        logger.debug(f"QR code detected (OpenCV): {data}")
            
        except Exception as e:
            logger.debug(f"OpenCV QR detection failed: {e}")
        
        return qr_data_list
    
    def _detect_datamatrix_pylibdmtx(self, roi: np.ndarray) -> List[str]:
        """
        Detect DataMatrix using pylibdmtx
        
        Args:
            roi: Input ROI image
        
        Returns:
            List of DataMatrix data strings
        """
        dmtx_data_list = []
        
        if not DMTX_AVAILABLE:
            return dmtx_data_list
        
        try:
            # Decode DataMatrix với timeout như testbase.py
            dmtx_codes = dmtx_decode(roi, timeout=100)
            
            if dmtx_codes:
                for dmtx_code in dmtx_codes:
                    data = dmtx_code.data.decode('utf-8', errors='ignore')
                    if data and data not in dmtx_data_list:
                        dmtx_data_list.append(data)
                        # Log với rect info như testbase.py
                        logger.info(f"✅ DataMatrix (pylibdmtx) detected: {data}")
                        logger.info(f"📐 Rect: {dmtx_code.rect}")
        
        except Exception as e:
            logger.debug(f"pylibdmtx decode failed: {e}")
        
        return dmtx_data_list
    
    def _detect_barcode_pyzbar(self, roi: np.ndarray) -> List[str]:
        """
        Detect DataMatrix only using pyzbar (filter only DataMatrix)
        
        Args:
            roi: Input ROI image
        
        Returns:
            List of DataMatrix data strings
        """
        barcode_data_list = []
        
        if not PYZBAR_AVAILABLE:
            return barcode_data_list
        
        try:
            # Decode barcodes (supports QR, DataMatrix, Code128, EAN, etc.)
            barcodes = pyzbar.decode(roi)
            
            if barcodes:
                for barcode in barcodes:
                    # Only accept DataMatrix
                    if barcode.type == 'DATAMATRIX':
                        data = barcode.data.decode('utf-8', errors='ignore')
                        if data and data not in barcode_data_list:
                            barcode_data_list.append(data)
                            logger.debug(f"DataMatrix (pyzbar) detected: {data}")
        
        except Exception as e:
            logger.debug(f"pyzbar decode failed: {e}")
        
        return barcode_data_list
    
    def _get_method_name(self, method: int) -> str:
        """Get method name for logging"""
        method_names = {
            0: "original",
            1: "clahe_binary",
            2: "clahe_denoise_binary",
            3: "adaptive_thresh",
            4: "otsu_thresh",
            5: "clahe_only",
            6: "denoise_clahe_binary",
            7: "invert_clahe_denoise_binary",
            8: "invert_only",
            9: "testbase_full",  # CLAHE + MedianBlur + AdaptiveThresh + Morphology
            10: "testbase_no_morph",  # CLAHE + MedianBlur + AdaptiveThresh
            11: "testbase_clahe"  # CLAHE only (clipLimit=2.0)
        }
        return method_names.get(method, f"method{method}")
    
    def _save_processed_image(self, processed_roi: np.ndarray, region_name: str, method: int, attempt: int):
        """
        Save processed image to logccd directory
        
        Args:
            processed_roi: Processed ROI image
            region_name: Region name
            method: Preprocessing method number
            attempt: Attempt number
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            method_name = self._get_method_name(method)
            filename = f"{timestamp}_{region_name}_{method_name}_attempt{attempt+1}.png"
            filepath = os.path.join(self.logccd_dir, filename)
            
            # Save image
            cv2.imwrite(filepath, processed_roi)
            logger.info(f"Saved processed image: {filepath}")
            
        except Exception as e:
            logger.warning(f"Failed to save processed image: {e}")
    
    def scan_barcodes(self, image: np.ndarray, template: Template, max_attempts: int = 12) -> Dict[str, List[str]]:
        """
        Scan DataMatrix only in crop regions (nếu scan_barcode=True)
        Saves processed images to logccd/ directory
        
        Args:
            image: Input image (already grayscale/mono)
            template: Template with crop regions
            max_attempts: Maximum preprocessing attempts (default: 9)
        
        Returns:
            Dictionary of {region_name: [barcode_data, ...]}
        """
        barcode_results = {}
        
        # Preprocessing method priority: theo testbase.py
        # Method 9: Testbase full (CLAHE + MedianBlur + AdaptiveThresh + Morphology) - BEST
        # Method 10: Testbase no morph (CLAHE + MedianBlur + AdaptiveThresh)
        # Method 11: Testbase CLAHE only (clipLimit=2.0)
        # Method 0: Original (gray)
        # Method 2: CLAHE + Denoise + Binarization
        # Method 7: Invert + CLAHE + Denoise + Binarization (white-on-dark)
        # Method 1: CLAHE + Binarization
        # Method 6: Denoise + CLAHE + Binarization
        # Method 8: Invert only
        # Method 3: Adaptive threshold
        # Method 4: Otsu threshold
        # Method 5: CLAHE only
        method_priority = [9, 10, 11, 0, 2, 7, 1, 6, 8, 3, 4, 5]
        
        for region in template.crop_regions:
            if not region.enabled or not region.scan_barcode:
                continue
            
            try:
                # Extract ROI
                x, y, w, h = region.x, region.y, region.width, region.height
                
                # Validate bounds
                img_h, img_w = image.shape[:2]
                x = max(0, min(x, img_w - 1))
                y = max(0, min(y, img_h - 1))
                w = max(1, min(w, img_w - x))
                h = max(1, min(h, img_h - y))
                
                # Extract ROI
                roi = image[y:y+h, x:x+w].copy()
                
                barcode_data_list = []
                found = False
                
                # Try multiple preprocessing methods (prioritize best methods first)
                for attempt in range(min(max_attempts, len(method_priority))):
                    if found:
                        break
                    
                    # Use priority order
                    method = method_priority[attempt]
                    
                    # Preprocess
                    processed_roi = self._preprocess_for_barcode(roi, method)
                    
                    # Save processed image to logccd/
                    self._save_processed_image(processed_roi, region.name, method, attempt)
                    
                    # Try pylibdmtx DataMatrix first (most reliable for DataMatrix)
                    if DMTX_AVAILABLE:
                        dmtx_data = self._detect_datamatrix_pylibdmtx(processed_roi)
                        if dmtx_data:
                            for data in dmtx_data:
                                if data and data not in barcode_data_list:
                                    barcode_data_list.append(data)
                                    logger.info(f"DataMatrix (pylibdmtx) found in '{region.name}' (method {method}, attempt {attempt+1}): {data}")
                                    found = True
                    
                    # Try pyzbar DataMatrix (filter only DataMatrix)
                    if not found and PYZBAR_AVAILABLE:
                        pyzbar_data = self._detect_barcode_pyzbar(processed_roi)
                        if pyzbar_data:
                            for data in pyzbar_data:
                                if data and data not in barcode_data_list:
                                    barcode_data_list.append(data)
                                    logger.info(f"DataMatrix (pyzbar) found in '{region.name}' (method {method}, attempt {attempt+1}): {data}")
                                    found = True
                
                if not barcode_data_list:
                    logger.warning(f"No DataMatrix found in '{region.name}' after {min(max_attempts, len(method_priority))} attempts")
                
                barcode_results[region.name] = barcode_data_list
                
            except Exception as e:
                logger.error(f"Failed to scan DataMatrix in '{region.name}': {e}")
                barcode_results[region.name] = []
        
        return barcode_results
    
    def process_image_with_template(self, image: np.ndarray, template: Template) -> Dict[str, Any]:
        """
        Process image with template: crop regions + scan barcodes
        
        Args:
            image: Input image
            template: Template
        
        Returns:
            Dictionary with results:
            {
                'cropped_images': {region_name: image},
                'barcodes': {region_name: [data, ...]},
                'success': bool
            }
        """
        try:
            # Crop regions
            cropped_images = self.crop_image_regions(image, template)
            
            # Scan barcodes
            barcodes = self.scan_barcodes(image, template)
            
            return {
                'cropped_images': cropped_images,
                'barcodes': barcodes,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to process image: {e}", exc_info=True)
            return {
                'cropped_images': {},
                'barcodes': {},
                'success': False,
                'error': str(e)
            }
    
    def draw_template_regions(self, image: np.ndarray, template: Template, 
                             draw_regions: bool = True) -> np.ndarray:
        """
        Draw template regions on image for visualization
        
        Args:
            image: Input image
            template: Template
            draw_regions: Draw crop regions
        
        Returns:
            Image with drawings
        """
        output = image.copy()
        
        # Draw crop regions
        if draw_regions:
            for region in template.crop_regions:
                if not region.enabled:
                    continue
                x, y, w, h = region.x, region.y, region.width, region.height
                
                # Màu khác nhau tùy vào có scan barcode không
                if region.scan_barcode:
                    # Màu xanh dương cho vùng có scan barcode
                    color = (255, 0, 0)  # BGR: blue
                    label = f"{region.name} (Crop+Barcode)"
                else:
                    # Màu xanh lá cho vùng chỉ crop
                    color = (0, 255, 0)  # BGR: green
                    label = f"{region.name} (Crop)"
                
                cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
                cv2.putText(output, label, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return output

