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
    
    def __init__(self, view, camera_service, template_service, template_dir: str = "templates/ccd1"):
        super().__init__()
        self._view = view
        self._camera_service = camera_service
        self._template_service = template_service
        self._template_dir = template_dir
        
        # State
        self._current_roi: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
        self._current_template = None
        self._last_frame: Optional[np.ndarray] = None
        self._test_image: Optional[np.ndarray] = None  # For testing
        
        # Camera settings service
        from app.service.camera_settings_service import CameraSettingsService
        self._settings_service = CameraSettingsService()
        
        # Use template service directory for images
        self._images_dir = os.path.join(self._template_service.templates_dir, "images")
        os.makedirs(self._images_dir, exist_ok=True)
        
        # Connect signals
        self._connect_signals()
        
        # Load templates
        self._load_templates()
        
        # Load saved camera settings
        self._load_camera_settings()
        
        logger.info("CCD1SettingPresenter initialized")
    
    def _connect_signals(self):
        """Connect view signals to presenter handlers"""
        self._view.roi_selected.connect(self.on_roi_selected)
        self._view.template_selected.connect(self.on_template_selected)
        self._view.set_pattern_requested.connect(self.on_set_pattern)
        self._view.threshold_changed.connect(self.on_threshold_changed)
        self._view.exposure_changed.connect(self.on_exposure_changed)
        self._view.gain_changed.connect(self.on_gain_changed)
        self._view.brightness_changed.connect(self.on_brightness_changed)
        self._view.contrast_changed.connect(self.on_contrast_changed)
        self._view.save_requested.connect(self.on_save_settings)
        self._view.cancel_requested.connect(self.on_cancel)
        
        # Test tab signals
        self._view.test_load_image_requested.connect(self.on_test_load_image)
        self._view.test_capture_requested.connect(self.on_test_capture)
        self._view.test_run_requested.connect(self.on_test_run)
    
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
    
    def _load_templates(self):
        """Load available templates"""
        try:
            templates = self._template_service.list_templates()
            self._view.update_template_list(templates)
            self._view.update_test_template_list(templates)  # Also update test tab
            logger.info(f"Loaded {len(templates)} templates for CCD1")
        except Exception as e:
            logger.error(f"Failed to load templates: {e}", exc_info=True)

    def on_template_selected(self, template_name: str):
        """Handle template selection"""
        try:
            template = self._template_service.load_template(template_name)
            if template:
                self._current_template = template
                # Set as system-wide current template
                self._template_service.set_current_template(template)
                
                # Check if CCD1 config is enabled and has image
                config = template.ccd1_config
                
                info = f"Template: {template.name}\n"
                
                if config.enabled and config.template_image_path:
                    info += f"Pattern: Set (Threshold: {config.match_threshold})\n"
                    # Load template image for matching visualization
                    if os.path.exists(config.template_image_path):
                        self._template_image = cv2.imread(config.template_image_path)
                        self._view.update_pattern_info(info + "Image loaded")
                    else:
                        self._view.update_pattern_info(info + "Image file missing")
                    
                    # Update threshold spinbox (block signals to avoid re-triggering save)
                    self._view.spin_threshold.blockSignals(True)
                    self._view.spin_threshold.setValue(config.match_threshold)
                    self._view.spin_threshold.blockSignals(False)
                    self._threshold = config.match_threshold
                else:
                    self._view.update_pattern_info(info + "No pattern set for CCD1")
                
                logger.info(f"Template loaded: {template_name}")
            else:
                self._view.update_pattern_info("Failed to load template")
                self._current_template = None
        except Exception as e:
            self._view.update_pattern_info(f"Error: {str(e)}")
            logger.error(f"Failed to load template: {e}", exc_info=True)

    def on_set_pattern(self):
        """Set current ROI as pattern for selected template"""
        if self._current_template is None:
            self._view.update_pattern_info("Please select a template first")
            return
            
        if self._current_roi is None:
            self._view.update_pattern_info("Please select ROI first")
            return
            
        if self._last_frame is None:
            return

        try:
            # Extract ROI
            x, y, w, h = self._current_roi
            roi = self._last_frame[y:y+h, x:x+w]
            self._template_image = roi.copy()
            
            # Save image
            image_filename = f"{self._current_template.name}_ccd1_pattern.png"
            image_path = os.path.join(self._images_dir, image_filename)
            cv2.imwrite(image_path, roi)
            
            # Update config
            # Keep existing config or create new
            config = self._current_template.ccd1_config
            config.enabled = True
            config.roi_x = x
            config.roi_y = y
            config.roi_width = w
            config.roi_height = h
            config.template_image_path = image_path
            config.match_threshold = self._threshold
            
            # Save template
            if self._template_service.save_template(self._current_template):
                self._view.update_pattern_info(f"Pattern saved! ({w}x{h})")
                logger.info(f"Pattern set for template '{self._current_template.name}'")
            else:
                self._view.update_pattern_info("Failed to save template")
                
        except Exception as e:
            self._view.update_pattern_info(f"Error: {str(e)}")
            logger.error(f"Failed to set pattern: {e}", exc_info=True)

    def on_threshold_changed(self, value: float):
        """Handle threshold change"""
        self._threshold = value
        logger.info(f"Threshold changed to {value}")
        
        # Update current template if loaded and pattern set
        if self._current_template and self._current_template.ccd1_config.enabled:
             self._current_template.ccd1_config.match_threshold = value
             self._template_service.save_template(self._current_template)
    
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
    
    # ========== Test Tab Handlers ==========
    
    def on_test_load_image(self):
        """Load image from file for testing"""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self._view,
                "Select Test Image",
                "",
                "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
            )
            
            if file_path:
                import cv2
                image = cv2.imread(file_path)
                
                if image is not None:
                    self._test_image = image
                    self._view.display_image(image)
                    
                    import os
                    filename = os.path.basename(file_path)
                    self._view.update_test_image_status(f"Loaded: {filename}")
                    logger.info(f"Test image loaded: {filename}")
                else:
                    self._view.update_test_image_status("Failed to load image")
                    logger.error("Failed to load test image")
        except Exception as e:
            logger.error(f"Error loading test image: {e}", exc_info=True)
            self._view.update_test_image_status("Error loading image")
    
    def on_test_capture(self):
        """Capture current frame from camera for testing"""
        try:
            if self._last_frame is not None:
                self._test_image = self._last_frame.copy()
                self._view.update_test_image_status("Captured from camera")
                logger.info("Test image captured from camera")
            else:
                self._view.update_test_image_status("No camera frame available")
                logger.warning("No camera frame available for test capture")
        except Exception as e:
            logger.error(f"Error capturing test image: {e}", exc_info=True)
            self._view.update_test_image_status("Error capturing image")
    
    def on_test_run(self):
        """Run test with current image and selected template"""
        try:
            if self._test_image is None:
                self._view.update_test_results("Error: No test image loaded")
                return
            
            # Get selected template
            template_name = self._view.combo_test_template.currentText()
            if not template_name:
                self._view.update_test_results("Error: No template selected")
                return
            
            # Load template
            template = self._template_service.load_template(template_name)
            if not template or not template.ccd1_config.enabled:
                self._view.update_test_results(f"Error: Template '{template_name}' not configured for CCD1")
                return
            
            # Run pattern matching
            result = self._template_service.match_ccd1_pattern(self._test_image, template)
            
            if result.get("success"):
                # Draw result on image
                display_frame = self._template_service.draw_ccd1_result(self._test_image.copy(), result)
                self._view.display_image(display_frame)
                
                # Format results
                score = result.get("score", 0.0)
                status = result.get("status", "UNKNOWN")
                threshold = template.ccd1_config.match_threshold
                
                result_text = f"Template: {template_name}\n"
                result_text += f"CCD1 Pattern Matching Results:\n"
                result_text += "-" * 40 + "\n\n"
                result_text += f"Match Score: {score:.4f}\n"
                result_text += f"Threshold: {threshold:.4f}\n"
                result_text += f"Status: {status}\n\n"
                
                if status == "OK":
                    result_text += "✓ Pattern matched successfully!"
                else:
                    result_text += "✗ Pattern does not match"
                
                self._view.update_test_results(result_text)
                logger.info(f"Test completed for template '{template_name}': {status}")
            else:
                error_msg = result.get("error", "Unknown error")
                self._view.update_test_results(f"Error: {error_msg}")
                logger.error(f"Test failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error running test: {e}", exc_info=True)
            self._view.update_test_results(f"Error: {str(e)}")
