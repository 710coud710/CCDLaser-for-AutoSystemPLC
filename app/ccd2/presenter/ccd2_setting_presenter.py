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
        
        # Connect signals
        self._connect_signals()
        
        # Load templates
        self._load_templates()
        
        logger.info("CCD2SettingPresenter initialized")
    
    def _connect_signals(self):
        """Connect view signals to presenter handlers"""
        self._view.roi_selected.connect(self.on_roi_selected)
        self._view.template_selected.connect(self.on_template_selected)
        self._view.region_add_requested.connect(self.on_region_add)
        self._view.region_edit_requested.connect(self.on_region_edit)
        self._view.region_delete_requested.connect(self.on_region_delete)
        self._view.process_test_requested.connect(self.on_process_test)
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
