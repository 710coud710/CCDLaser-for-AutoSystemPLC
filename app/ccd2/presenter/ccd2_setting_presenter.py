"""
CCD2 Setting Presenter - Xử lý logic cho CCD2 Setting
Chức năng:
- Quản lý template và regions
- Datamatrix scanning
- Test processing
"""
import logging
import numpy as np
import cv2
from typing import Optional
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class CCD2SettingPresenter(QObject):
    """
    Presenter cho CCD2 Setting View
    - Xử lý template và regions
    - Datamatrix scanning
    """
    
    def __init__(self, view, camera_service, template_service):
        super().__init__()
        self._view = view
        self._camera_service = camera_service
        self._template_service = template_service
        
        # State
        self._current_template = None
        self._current_roi: Optional[tuple] = None
        self._last_frame: Optional[np.ndarray] = None
        self._master_image: Optional[np.ndarray] = None  # For new template creation
        
        # Camera settings service
        from app.service.camera_settings_service import CameraSettingsService
        self._settings_service = CameraSettingsService()
        
        # Connect signals
        self._connect_signals()
        
        # Load templates
        self._load_templates()
        
        # Load saved camera settings
        self._load_camera_settings()
        
        logger.info("CCD2SettingPresenter initialized")
    
    def _connect_signals(self):
        """Connect view signals to presenter handlers"""
        self._view.roi_selected.connect(self.on_roi_selected)
        self._view.template_selected.connect(self.on_template_selected)
        self._view.region_add_requested.connect(self.on_region_add)
        self._view.region_edit_requested.connect(self.on_region_edit)
        self._view.region_delete_requested.connect(self.on_region_delete)
        self._view.process_test_requested.connect(self.on_process_test)
        self._view.capture_master_requested.connect(self.on_capture_master)
        self._view.save_new_template_requested.connect(self.on_save_new_template)
        self._view.exposure_changed.connect(self.on_exposure_changed)
        self._view.gain_changed.connect(self.on_gain_changed)
        self._view.brightness_changed.connect(self.on_brightness_changed)
        self._view.contrast_changed.connect(self.on_contrast_changed)
        self._view.save_requested.connect(self.on_save_settings)
        self._view.cancel_requested.connect(self.on_cancel)
    
    def _load_templates(self):
        """Load available templates"""
        try:
            templates = self._template_service.list_templates()
            self._view.update_template_list(templates)
            logger.info(f"Loaded {len(templates)} templates")
        except Exception as e:
            logger.error(f"Failed to load templates: {e}", exc_info=True)
    
    def _load_camera_settings(self):
        """Load saved camera settings và update UI"""
        try:
            settings = self._settings_service.load_settings("ccd2")
            
            # Update UI với saved settings
            self._view.spin_exposure.setValue(settings.get("exposure", 10000))
            self._view.spin_gain.setValue(settings.get("gain", 0))
            self._view.slider_brightness.setValue(settings.get("brightness", 50))
            self._view.slider_contrast.setValue(settings.get("contrast", 0))
            
            logger.info(f"Loaded camera settings for CCD2: {settings}")
        except Exception as e:
            logger.error(f"Failed to load camera settings: {e}", exc_info=True)
    
    def on_roi_selected(self, x: int, y: int, width: int, height: int):
        """Handle ROI selection"""
        self._current_roi = (x, y, width, height)
        logger.info(f"ROI selected: {self._current_roi}")
    
    def on_template_selected(self, template_name: str):
        """Handle template selection"""
        try:
            template = self._template_service.load_template(template_name)
            if template:
                self._current_template = template
                
                # Update template info
                info = f"Template: {template.name}\n"
                info += f"{template.description}\n"
                info += f"Regions: {len(template.crop_regions)}"
                self._view.update_template_info(info)
                
                # Update regions table
                self._view.update_regions_table(template.crop_regions)
                
                logger.info(f"Template loaded: {template_name}")
            else:
                self._view.update_template_info("Failed to load template")
                logger.error(f"Failed to load template: {template_name}")
        except Exception as e:
            self._view.update_template_info(f"Error: {str(e)}")
            logger.error(f"Failed to load template: {e}", exc_info=True)
    
    def on_region_add(self):
        """Handle add region request"""
        if self._current_roi is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No ROI",
                "Please select a ROI on the image first"
            )
            return
        
        if self._current_template is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No Template",
                "Please select a template first"
            )
            return
        
        # Add region to template
        try:
            from PySide6.QtWidgets import QInputDialog
            
            name, ok = QInputDialog.getText(
                self._view,
                "Region Name",
                "Enter region name:"
            )
            
            if ok and name:
                from app.model.template_data import CropRegion
                
                x, y, w, h = self._current_roi
                region = CropRegion(
                    name=name,
                    x=x, y=y,
                    width=w, height=h,
                    enabled=True,
                    scan_barcode=True
                )
                
                self._current_template.crop_regions.append(region)
                
                # Save template
                if self._template_service.save_template(self._current_template):
                    self._view.update_regions_table(self._current_template.crop_regions)
                    logger.info(f"Region '{name}' added to template")
                else:
                    logger.error("Failed to save template after adding region")
        except Exception as e:
            logger.error(f"Failed to add region: {e}", exc_info=True)
    
    def on_region_edit(self, index: int):
        """Handle edit region request"""
        if self._current_template is None:
            return
        
        if index < 0 or index >= len(self._current_template.crop_regions):
            return
        
        if self._current_roi is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No ROI",
                "Please select a new ROI on the image first"
            )
            return
        
        try:
            # Update region with new ROI
            region = self._current_template.crop_regions[index]
            x, y, w, h = self._current_roi
            
            region.x = x
            region.y = y
            region.width = w
            region.height = h
            
            # Save template
            if self._template_service.save_template(self._current_template):
                self._view.update_regions_table(self._current_template.crop_regions)
                logger.info(f"Region '{region.name}' updated")
            else:
                logger.error("Failed to save template after editing region")
        except Exception as e:
            logger.error(f"Failed to edit region: {e}", exc_info=True)
    
    def on_region_delete(self, index: int):
        """Handle delete region request"""
        if self._current_template is None:
            return
        
        if index < 0 or index >= len(self._current_template.crop_regions):
            return
        
        try:
            from PySide6.QtWidgets import QMessageBox
            
            region = self._current_template.crop_regions[index]
            reply = QMessageBox.question(
                self._view,
                "Delete Region",
                f"Are you sure you want to delete region '{region.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._current_template.crop_regions.pop(index)
                
                # Save template
                if self._template_service.save_template(self._current_template):
                    self._view.update_regions_table(self._current_template.crop_regions)
                    logger.info(f"Region '{region.name}' deleted")
                else:
                    logger.error("Failed to save template after deleting region")
        except Exception as e:
            logger.error(f"Failed to delete region: {e}", exc_info=True)
    
    def on_process_test(self):
        """Handle process test request"""
        if self._current_template is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No Template",
                "Please select a template first"
            )
            return
        
        if self._last_frame is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No Frame",
                "No frame available for processing"
            )
            return
        
        try:
            # Process frame with template
            results = self._template_service.process_image_with_template(
                self._last_frame,
                self._current_template
            )
            
            if results['success']:
                # Format results
                results_text = ""
                barcodes = results.get('barcodes', {})
                
                if barcodes:
                    results_text += "=== Barcodes ===\n"
                    for region_name, barcode_list in barcodes.items():
                        if barcode_list:
                            for barcode_data in barcode_list:
                                results_text += f"{region_name}: {barcode_data}\n"
                        else:
                            results_text += f"{region_name}: No barcode detected\n"
                else:
                    results_text = "No barcodes detected"
                
                self._view.update_results(results_text.strip())
                logger.info("Test processing completed")
            else:
                error_msg = results.get('error', 'Unknown error')
                self._view.update_results(f"Error: {error_msg}")
                logger.error(f"Test processing failed: {error_msg}")
        except Exception as e:
            self._view.update_results(f"Error: {str(e)}")
            logger.error(f"Failed to process test: {e}", exc_info=True)
    
    def on_capture_master(self):
        """Capture current frame as master image for new template"""
        if self._last_frame is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No Frame",
                "No frame available to capture"
            )
            return
        
        try:
            # Capture current frame as master image
            self._master_image = self._last_frame.copy()
            
            h, w = self._master_image.shape[:2]
            self._view.update_master_status(f"Master image captured: {w}x{h}", enable_save=True)
            logger.info(f"Master image captured: {w}x{h}")
        except Exception as e:
            self._view.update_master_status(f"Error: {str(e)}", enable_save=False)
            logger.error(f"Failed to capture master image: {e}", exc_info=True)
    
    def on_save_new_template(self, name: str, description: str):
        """Save new template with captured master image and regions"""
        if self._master_image is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._view,
                "No Master Image",
                "Please capture a master image first"
            )
            return
        
        try:
            from app.model.template_data import Template
            
            # Create new template
            h, w = self._master_image.shape[:2]
            new_template = Template(
                name=name,
                description=description,
                crop_regions=[],  # Start with empty regions, user can add later
                master_image_width=w,
                master_image_height=h
            )
            
            # Save template
            if self._template_service.save_template(new_template):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self._view,
                    "Success",
                    f"Template '{name}' created successfully!\nYou can now add regions to it."
                )
                
                # Reload templates list
                self._load_templates()
                
                # Select the new template
                self._current_template = new_template
                self._view.update_template_info(f"Template: {name}\n{description}\nRegions: 0")
                self._view.update_regions_table([])
                
                # Clear master image and form
                self._master_image = None
                self._view.update_master_status("No master image captured", enable_save=False)
                
                logger.info(f"New template '{name}' created successfully")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self._view,
                    "Error",
                    f"Failed to save template '{name}'"
                )
                logger.error(f"Failed to save new template '{name}'")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self._view,
                "Error",
                f"Failed to create template: {str(e)}"
            )
            logger.error(f"Failed to create new template: {e}", exc_info=True)
    
    def on_exposure_changed(self, value: int):
        """Handle exposure change"""
        logger.info(f"Exposure changed to {value} μs")
        # Save to settings
        self._settings_service.update_parameter("ccd2", "exposure", value)
        # TODO: Apply exposure to camera service if available
        # if self._camera_service:
        #     self._camera_service.set_parameter('ExposureTime', value)
    
    def on_gain_changed(self, value: int):
        """Handle gain change"""
        logger.info(f"Gain changed to {value} dB")
        # Save to settings
        self._settings_service.update_parameter("ccd2", "gain", value)
        # TODO: Apply gain to camera service if available
        # if self._camera_service:
        #     self._camera_service.set_parameter('Gain', value)
    
    def on_brightness_changed(self, value: int):
        """Handle brightness change"""
        logger.info(f"Brightness changed to {value}")
        # Save to settings
        self._settings_service.update_parameter("ccd2", "brightness", value)
        # Brightness is typically applied in post-processing
    
    def on_contrast_changed(self, value: int):
        """Handle contrast change"""
        logger.info(f"Contrast changed to {value}")
        # Save to settings
        self._settings_service.update_parameter("ccd2", "contrast", value)
        # Contrast is typically applied in post-processing
    
    def on_save_settings(self):
        """Save settings and close"""
        logger.info("Save settings requested")
        # Settings are already saved when template is modified
        self._view.close()
    
    def on_cancel(self):
        """Cancel and close without saving"""
        logger.info("Cancel requested")
        self._view.close()
    
    def update_frame(self, frame: np.ndarray):
        """Update display with new frame"""
        try:
            self._last_frame = frame.copy()
            display_frame = frame.copy()
            
            # Draw template regions if template is loaded
            if self._current_template is not None:
                display_frame = self._template_service.draw_template_regions(
                    display_frame,
                    self._current_template,
                    draw_regions=True
                )
            
            # Display frame
            self._view.display_image(display_frame)
        except Exception as e:
            logger.error(f"Failed to update frame: {e}", exc_info=True)
