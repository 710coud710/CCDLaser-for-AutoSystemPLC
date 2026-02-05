"""
CCD1 Setting Presenter - Xử lý logic cho CCD1 Setting
Chức năng:
- Quản lý ROI selection
- Template matching với threshold
- Lưu/load template
"""
import logging
import numpy as np
import cv2
import os
from typing import Optional, Tuple
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class CCD1SettingPresenter(QObject):
    """
    Presenter cho CCD1 Setting View
    - Xử lý ROI selection
    - Template matching
    - Lưu/load template
    """
    
    def __init__(self, view, camera_service, template_dir: str = "templates/ccd1"):
        super().__init__()
        self._view = view
        self._camera_service = camera_service
        self._template_dir = template_dir
        
        # State
        self._current_roi: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
        self._template_image: Optional[np.ndarray] = None
        self._template_path: Optional[str] = None
        self._threshold: float = 0.8
        self._last_frame: Optional[np.ndarray] = None
        
        # Camera settings service
        from app.service.camera_settings_service import CameraSettingsService
        self._settings_service = CameraSettingsService()
        
        # Create template directory
        os.makedirs(self._template_dir, exist_ok=True)
        
        # Connect signals
        self._connect_signals()
        
        # Load saved camera settings
        self._load_camera_settings()
        
        logger.info("CCD1SettingPresenter initialized")
    
    def _connect_signals(self):
        """Connect view signals to presenter handlers"""
        self._view.roi_selected.connect(self.on_roi_selected)
        self._view.template_capture_requested.connect(self.on_capture_template)
        self._view.template_load_requested.connect(self.on_load_template)
        self._view.threshold_changed.connect(self.on_threshold_changed)
        self._view.exposure_changed.connect(self.on_exposure_changed)
        self._view.gain_changed.connect(self.on_gain_changed)
        self._view.brightness_changed.connect(self.on_brightness_changed)
        self._view.contrast_changed.connect(self.on_contrast_changed)
        self._view.save_requested.connect(self.on_save_settings)
        self._view.cancel_requested.connect(self.on_cancel)
    
    def _load_camera_settings(self):
        """Load saved camera settings và update UI"""
        try:
            settings = self._settings_service.load_settings("ccd1")
            
            # Update UI với saved settings
            self._view.spin_exposure.setValue(settings.get("exposure", 10000))
            self._view.spin_gain.setValue(settings.get("gain", 0))
            self._view.slider_brightness.setValue(settings.get("brightness", 50))
            self._view.slider_contrast.setValue(settings.get("contrast", 0))
            
            logger.info(f"Loaded camera settings for CCD1: {settings}")
        except Exception as e:
            logger.error(f"Failed to load camera settings: {e}", exc_info=True)
    
    def on_roi_selected(self, x: int, y: int, width: int, height: int):
        """Handle ROI selection"""
        self._current_roi = (x, y, width, height)
        logger.info(f"ROI selected: {self._current_roi}")
    
    def on_capture_template(self):
        """Capture current frame and use ROI as template (no file dialog)"""
        if self._current_roi is None:
            self._view.update_template_status("Error: No ROI selected")
            logger.warning("Cannot capture template: No ROI selected")
            return
        
        if self._last_frame is None:
            self._view.update_template_status("Error: No frame available")
            logger.warning("Cannot capture template: No frame available")
            return
        
        try:
            # Extract ROI from current frame
            x, y, w, h = self._current_roi
            roi = self._last_frame[y:y+h, x:x+w]
            
            # Use ROI directly as template (no save to file)
            self._template_image = roi.copy()
            
            # Optionally save to file for persistence
            template_path = os.path.join(self._template_dir, "template.png")
            cv2.imwrite(template_path, roi)
            self._template_path = template_path
            
            self._view.update_template_status(f"Template captured: {w}x{h}")
            logger.info(f"Template captured from stream and saved to {template_path}")
        except Exception as e:
            self._view.update_template_status(f"Error: {str(e)}")
            logger.error(f"Failed to capture template: {e}", exc_info=True)
    
    def on_load_template(self):
        """Load template from file"""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self._view,
                "Load Template",
                self._template_dir,
                "Images (*.png *.jpg *.bmp)"
            )
            
            if not file_path:
                return
            
            # Load template image
            template = cv2.imread(file_path)
            if template is None:
                self._view.update_template_status("Error: Failed to load image")
                logger.error(f"Failed to load template from {file_path}")
                return
            
            self._template_image = template
            self._template_path = file_path
            
            h, w = template.shape[:2]
            self._view.update_template_status(f"Template loaded: {w}x{h}")
            logger.info(f"Template loaded from {file_path}")
        except Exception as e:
            self._view.update_template_status(f"Error: {str(e)}")
            logger.error(f"Failed to load template: {e}", exc_info=True)
    
    def on_threshold_changed(self, value: float):
        """Handle threshold change"""
        self._threshold = value
        logger.info(f"Threshold changed to {value}")
    
    def on_exposure_changed(self, value: int):
        """Handle exposure change"""
        logger.info(f"Exposure changed to {value} μs")
        # Save to settings
        self._settings_service.update_parameter("ccd1", "exposure", value)
        # TODO: Apply exposure to camera service if available
        # if self._camera_service:
        #     self._camera_service.set_parameter('ExposureTime', value)
    
    def on_gain_changed(self, value: int):
        """Handle gain change"""
        logger.info(f"Gain changed to {value} dB")
        # Save to settings
        self._settings_service.update_parameter("ccd1", "gain", value)
        # TODO: Apply gain to camera service if available
        # if self._camera_service:
        #     self._camera_service.set_parameter('Gain', value)
    
    def on_brightness_changed(self, value: int):
        """Handle brightness change"""
        logger.info(f"Brightness changed to {value}")
        # Save to settings
        self._settings_service.update_parameter("ccd1", "brightness", value)
        # Brightness is typically applied in post-processing
    
    def on_contrast_changed(self, value: int):
        """Handle contrast change"""
        logger.info(f"Contrast changed to {value}")
        # Save to settings
        self._settings_service.update_parameter("ccd1", "contrast", value)
        # Contrast is typically applied in post-processing
    
    def on_save_settings(self):
        """Save settings and close"""
        logger.info("Save settings requested")
        # Settings are already saved when template is saved
        self._view.close()
    
    def on_cancel(self):
        """Cancel and close without saving"""
        logger.info("Cancel requested")
        self._view.close()
    
    def update_frame(self, frame: np.ndarray):
        """Update display with new frame and perform matching if template exists"""
        try:
            self._last_frame = frame.copy()
            display_frame = frame.copy()
            
            # Perform template matching if template and ROI exist
            if self._template_image is not None and self._current_roi is not None:
                match_result = self._perform_template_matching(frame)
                
                # Draw ROI on frame if enabled
                if self._view.get_show_roi():
                    x, y, w, h = self._current_roi
                    color = (0, 255, 0) if match_result['match'] else (0, 0, 255)
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                    
                    # Draw match status
                    status_text = "OK" if match_result['match'] else "ERROR"
                    cv2.putText(
                        display_frame, status_text,
                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, color, 2
                    )
                
                # Update results
                self._update_match_results(match_result)
            
            # Display frame
            self._view.display_image(display_frame)
        except Exception as e:
            logger.error(f"Failed to update frame: {e}", exc_info=True)
    
    def _perform_template_matching(self, frame: np.ndarray) -> dict:
        """Perform template matching at ROI location"""
        try:
            if self._template_image is None or self._current_roi is None:
                return {'match': False, 'score': 0.0, 'error': 'No template or ROI'}
            
            x, y, w, h = self._current_roi
            
            # Extract ROI from frame
            roi = frame[y:y+h, x:x+w]
            
            # Convert to grayscale for matching
            if len(roi.shape) == 3:
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                roi_gray = roi
            
            if len(self._template_image.shape) == 3:
                template_gray = cv2.cvtColor(self._template_image, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = self._template_image
            
            # Resize template to match ROI size if needed
            if template_gray.shape != roi_gray.shape:
                template_gray = cv2.resize(template_gray, (roi_gray.shape[1], roi_gray.shape[0]))
            
            # Compute similarity using normalized correlation
            result = cv2.matchTemplate(roi_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Check if match exceeds threshold
            match = max_val >= self._threshold
            
            return {
                'match': match,
                'score': float(max_val),
                'threshold': self._threshold,
                'location': max_loc
            }
        except Exception as e:
            logger.error(f"Template matching failed: {e}", exc_info=True)
            return {'match': False, 'score': 0.0, 'error': str(e)}
    
    def _update_match_results(self, result: dict):
        """Update match results display"""
        try:
            results_text = ""
            
            if 'error' in result:
                results_text = f"Error: {result['error']}\n"
            else:
                status = "OK" if result['match'] else "ERROR"
                score = result.get('score', 0.0)
                threshold = result.get('threshold', self._threshold)
                
                results_text += f"Status: {status}\n"
                results_text += f"Match Score: {score:.4f}\n"
                results_text += f"Threshold: {threshold:.4f}\n"
                
                if result['match']:
                    results_text += "\n✓ Template matched successfully"
                else:
                    results_text += "\n✗ Template does not match"
            
            self._view.update_results(results_text.strip())
        except Exception as e:
            logger.error(f"Failed to update match results: {e}", exc_info=True)
