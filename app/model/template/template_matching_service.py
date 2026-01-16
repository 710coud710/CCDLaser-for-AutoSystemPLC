"""
Template Matching Service - So khớp vị trí panel với template
Sử dụng OpenCV Template Matching
"""
import cv2
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Kết quả template matching"""
    success: bool
    # Vị trí tìm được (top-left corner)
    x: int = 0
    y: int = 0
    # Độ lệch so với vị trí chuẩn
    dx: int = 0
    dy: int = 0
    # Góc xoay (chưa implement)
    angle: float = 0.0
    # Điểm số matching (0-1)
    score: float = 0.0
    # Thông tin debug
    method: str = ""
    message: str = ""


class TemplateMatchingService:
    """
    Template Matching Service
    - So khớp template region trên ảnh mới
    - Tính toán offset (dx, dy, angle)
    - Kiểm tra tolerance
    """
    
    def __init__(self):
        # Template matching methods
        # TM_CCOEFF_NORMED: Correlation coefficient (normalized)
        # TM_CCORR_NORMED: Cross correlation (normalized)
        # TM_SQDIFF_NORMED: Squared difference (normalized, inverted)
        self.method = cv2.TM_CCOEFF_NORMED
        logger.info("TemplateMatchingService initialized")
    
    def match_template(
        self,
        image: np.ndarray,
        template: np.ndarray,
        template_x: int,
        template_y: int,
        search_margin: int = 50,
        min_score: float = 0.7
    ) -> MatchResult:
        """
        So khớp template trên image
        
        Args:
            image: Ảnh đầu vào (panel mới)
            template: Template ROI (từ recipe)
            template_x, template_y: Vị trí chuẩn của template trên ảnh master
            search_margin: Vùng tìm kiếm xung quanh vị trí chuẩn (pixel)
            min_score: Điểm số tối thiểu để chấp nhận
        
        Returns:
            MatchResult
        """
        try:
            if image is None or template is None:
                return MatchResult(
                    success=False,
                    message="Invalid input image or template"
                )
            
            # Validate dimensions
            img_h, img_w = image.shape[:2]
            tpl_h, tpl_w = template.shape[:2]
            
            if tpl_h > img_h or tpl_w > img_w:
                return MatchResult(
                    success=False,
                    message=f"Template ({tpl_w}x{tpl_h}) larger than image ({img_w}x{img_h})"
                )
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                image_gray = image.copy()
            
            if len(template.shape) == 3:
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template.copy()
            
            # Define search region (ROI around expected position)
            # Search region should be large enough to contain the template + margin
            search_x1 = max(0, template_x - search_margin)
            search_y1 = max(0, template_y - search_margin)
            search_x2 = min(img_w, template_x + tpl_w + search_margin)
            search_y2 = min(img_h, template_y + tpl_h + search_margin)
            
            # Ensure valid search region
            if search_x2 <= search_x1 or search_y2 <= search_y1:
                # Search region invalid, search entire image
                logger.warning("Search region invalid, searching entire image")
                search_roi = image_gray
                search_x1 = 0
                search_y1 = 0
            else:
                # Extract search ROI
                search_roi = image_gray[search_y1:search_y2, search_x1:search_x2]
            
            # Perform template matching
            result = cv2.matchTemplate(search_roi, template_gray, self.method)
            
            # Find best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # For TM_CCOEFF_NORMED and TM_CCORR_NORMED, higher is better
            # For TM_SQDIFF_NORMED, lower is better
            if self.method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                match_score = 1.0 - min_val
                match_loc = min_loc
            else:
                match_score = max_val
                match_loc = max_loc
            
            # Convert to absolute coordinates
            match_x = search_x1 + match_loc[0]
            match_y = search_y1 + match_loc[1]
            
            # Calculate offset
            dx = match_x - template_x
            dy = match_y - template_y
            
            # Check score threshold
            if match_score < min_score:
                return MatchResult(
                    success=False,
                    x=match_x,
                    y=match_y,
                    dx=dx,
                    dy=dy,
                    score=match_score,
                    method="TM_CCOEFF_NORMED",
                    message=f"Match score {match_score:.3f} below threshold {min_score}"
                )
            
            logger.info(
                f"Template matched: pos=({match_x}, {match_y}), "
                f"offset=({dx:+d}, {dy:+d}), score={match_score:.3f}"
            )
            
            return MatchResult(
                success=True,
                x=match_x,
                y=match_y,
                dx=dx,
                dy=dy,
                angle=0.0,  # TODO: Implement rotation detection
                score=match_score,
                method="TM_CCOEFF_NORMED",
                message="Match successful"
            )
            
        except Exception as e:
            logger.error(f"Template matching error: {e}", exc_info=True)
            return MatchResult(
                success=False,
                message=f"Exception: {str(e)}"
            )
    
    def check_tolerance(
        self,
        match_result: MatchResult,
        max_dx: float,
        max_dy: float,
        max_angle: float
    ) -> Tuple[bool, str]:
        """
        Kiểm tra xem kết quả matching có nằm trong tolerance không
        
        Args:
            match_result: Kết quả matching
            max_dx, max_dy, max_angle: Ngưỡng cho phép
        
        Returns:
            (is_valid, message)
        """
        if not match_result.success:
            return False, match_result.message
        
        # Check position offset
        if abs(match_result.dx) > max_dx:
            return False, f"X offset {match_result.dx:+d} exceeds limit ±{max_dx}"
        
        if abs(match_result.dy) > max_dy:
            return False, f"Y offset {match_result.dy:+d} exceeds limit ±{max_dy}"
        
        # Check angle (TODO: implement rotation detection)
        if abs(match_result.angle) > max_angle:
            return False, f"Angle {match_result.angle:+.2f}° exceeds limit ±{max_angle}°"
        
        return True, "Within tolerance"
    
    def draw_match_result(
        self,
        image: np.ndarray,
        match_result: MatchResult,
        template_width: int,
        template_height: int,
        template_x: int = 0,
        template_y: int = 0
    ) -> np.ndarray:
        """
        Vẽ kết quả matching lên ảnh
        
        Args:
            image: Ảnh đầu vào
            match_result: Kết quả matching
            template_width, template_height: Kích thước template
            template_x, template_y: Vị trí chuẩn (để vẽ reference)
        
        Returns:
            Ảnh đã vẽ
        """
        output = image.copy()
        
        if not match_result.success:
            # Draw error message
            cv2.putText(
                output,
                f"Match Failed: {match_result.message}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            return output
        
        # Draw matched position (green)
        cv2.rectangle(
            output,
            (match_result.x, match_result.y),
            (match_result.x + template_width, match_result.y + template_height),
            (0, 255, 0),
            2
        )
        
        # Draw reference position (blue) if provided
        if template_x > 0 or template_y > 0:
            cv2.rectangle(
                output,
                (template_x, template_y),
                (template_x + template_width, template_y + template_height),
                (255, 0, 0),
                2
            )
        
        # Draw offset arrow
        center_ref = (
            template_x + template_width // 2,
            template_y + template_height // 2
        )
        center_match = (
            match_result.x + template_width // 2,
            match_result.y + template_height // 2
        )
        cv2.arrowedLine(
            output,
            center_ref,
            center_match,
            (0, 255, 255),
            2,
            tipLength=0.3
        )
        
        # Draw info text
        info_text = [
            f"Score: {match_result.score:.3f}",
            f"Offset: ({match_result.dx:+d}, {match_result.dy:+d}) px",
            f"Angle: {match_result.angle:+.2f} deg"
        ]
        
        for i, text in enumerate(info_text):
            cv2.putText(
                output,
                text,
                (10, 30 + i * 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )
        
        return output


