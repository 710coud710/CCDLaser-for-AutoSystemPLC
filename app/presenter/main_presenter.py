"""
Main Presenter - Điều phối giữa View và Model
Theo MVP: Presenter chứa logic, không biết chi tiết UI
"""
import logging
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
import cv2
from PySide6.QtCore import QObject, QTimer
from app.view.view_interface import IView, IPresenter
from app.model import CameraConnectionService
from app.model.qr import QRDetectionService, QRDetectionResult
from app.model.recipe import RecipeService, Recipe, TemplateRegion, QRROIRegion, Tolerance
from app.model.template import TemplateMatchingService, MatchResult
from app.model.template_data import TemplateService, Template, CropRegion
from .state_machine import StateMachine, AppState
from services.remoteTcpServer import RemoteTcpClient
from services.logService import getLogger
from app.model.camera.ccd_worker import CCDWorker
logger = getLogger(__name__)

class MainPresenter(QObject):
    """
    Main Presenter
    - Điều phối giữa View và Model
    - Quản lý state machine
    - Xử lý business logic
    """
    
    def __init__(self, view: IView, settings: dict):
        super().__init__()
        self._view = view
        self._settings = settings
        
        # Model - Camera Service (CCD2 - hiện tại)
        self._camera_service = CameraConnectionService()

        # CCD1 worker (QThread) - camera độc lập
        self._ccd1_worker: Optional[CCDWorker] = None
        
        # QR Detection Service (deprecated, using template service now)
        qr_config = settings.get('qr', {})
        self._qr_service = QRDetectionService(qr_config) if qr_config else None
        self._qr_enabled = False
        
        # Barcode detection enabled flag
        self._barcode_enabled = True  # Default enabled
        
        # Recipe Service
        self._recipe_service = RecipeService()
        
        # Template Matching Service
        self._template_matching_service = TemplateMatchingService()
        
        # Template Service (NEW - Simple template system)
        self._template_service = TemplateService()
        
        # Camera Settings Service
        from services.cameraSettingsService import CameraSettingsService
        self._camera_settings_service = CameraSettingsService()
        
        # Template mode state (for editing templates)
        self._template_master_image = None
        self._template_crop_regions = []  # Crop regions (có thể có scan_barcode)
        self._template_test_image = None
        
        # Running mode state
        self._last_match_result = None
        
        # Test image for running mode (without camera)
        self._test_image = None
        self._test_image_path = None
        
        # State machine
        self._state_machine = StateMachine()
        self._state_machine.set_state_change_callback(self._on_state_changed)
        
        # Timer cho streaming
        self._stream_timer = QTimer()
        self._stream_timer.timeout.connect(self._on_stream_timer)
        self._stream_interval = 33  # ~30 FPS

        # Cache latest camera frame (for remote CHECK when streaming)
        self._last_camera_frame = None

        # Remote TCP client
        self._remote_client = RemoteTcpClient()
        self._remote_check_busy = False
        
        # ScreenCCD directory for saving captured images
        self._screenccd_dir = self._get_screenccd_directory()
        os.makedirs(self._screenccd_dir, exist_ok=True)
        logger.info(f"ScreenCCD directory: {self._screenccd_dir}")
        
        logger.info("MainPresenter initialized")
    
    # ========== IPresenter Implementation ==========
    
    def on_view_ready(self):
        """View đã sẵn sàng"""
        logger.info("View ready")
        self._view.update_status("idle")
        self._view.show_message("Application ready", "info")
        
        # Load template list
        templates = self._template_service.list_templates()
        self._view.update_template_list(templates)
        logger.info(f"Loaded {len(templates)} template(s)")
        
        # Load camera settings if available
        settings = self._camera_settings_service.load_settings()
        if settings:
            logger.info("Loaded saved camera settings")

        # Connect to remote TCP server if enabled
        tcp_cfg = (self._settings.get("tcp_server", {}) or {})
        if tcp_cfg.get("enabled", False):
            host = tcp_cfg.get("host", "localhost")
            port = int(tcp_cfg.get("port", 9000))
            self._remote_client.messageReceived.connect(self._on_remote_message)
            self._remote_client.connected.connect(lambda: self._view.show_message(f"Connected to TCP server at {host}:{port}", "info"))
            self._remote_client.disconnected.connect(lambda: logger.warning("Disconnected from TCP server"))
            ok = self._remote_client.connect_to_server(host, port)
            if not ok:
                self._view.show_message("Failed to connect to TCP server", "warning")
    
    def on_view_closing(self):
        """View sắp đóng - cleanup"""
        logger.info("View closing - cleaning up...")

        # Dừng CCD1 worker nếu còn chạy
        try:
            if self._ccd1_worker is not None:
                logger.info("Stopping CCD1 worker on view closing...")
                self._ccd1_worker.stop()
                self._ccd1_worker.wait(2000)
                self._ccd1_worker = None
        except Exception as e:
            logger.error(f"Failed to stop CCD1 worker: {e}", exc_info=True)
        
        # Stop streaming nếu đang chạy
        if self._state_machine.is_streaming():
            self._stop_streaming()
        
        # Disconnect camera nếu đang connected
        if self._state_machine.is_connected():
            self._disconnect_camera()
        
        # Cleanup
        try:
            self._remote_client.disconnect_from_server()
        except Exception:
            pass
        self._camera_service.cleanup()
        logger.info("Cleanup completed")
    
    def on_connect_clicked(self):
        """User click Connect"""
        logger.info("Connect button clicked")
        
        if not self._state_machine.can_transition_to(AppState.CONNECTING):
            self._view.show_message("Cannot connect in current state", "warning")
            return
        
        # 1) Kết nối + start streaming cho CCD2 (camera chính)
        self._connect_camera()

        # 2) Tự động start CCD1 trong QThread riêng (nếu cấu hình cho phép)
        try:
            logger.info("Auto-start CCD1 after main camera connect...")
            self.on_ccd1_start_clicked()
        except Exception as e:
            # Không làm hỏng CCD2 nếu CCD1 lỗi; chỉ log + thông báo nhẹ
            logger.error(f"Auto-start CCD1 failed: {e}", exc_info=True)
            self._view.show_message(f"CCD1 auto-start failed: {e}", "warning")

    # ========== CCD1 Handlers (QThread, độc lập với CCD2) ==========

    def on_ccd1_start_clicked(self):
        """
        Start CCD1 trong QThread riêng.
        - Dùng cấu hình camera_ccd1 trong setting/camera.yaml
        """
        logger.info("CCD1 start requested")

        if self._ccd1_worker is not None and self._ccd1_worker.isRunning():
            self._view.show_message("CCD1 is already running", "info")
            return

        # Lấy config CCD1 (camera_ccd1). Nếu không có thì fallback ip="0"
        ccd1_cfg = (self._settings.get("camera_ccd1", {}) or {})
        camera_id = ccd1_cfg.get("ip", "0")

        try:
            self._ccd1_worker = CCDWorker(str(camera_id), ccd1_cfg)
            self._ccd1_worker.frameCaptured.connect(self._on_ccd1_frame_captured)
            self._ccd1_worker.start()

            # Cập nhật UI cho CCD1 nếu view hỗ trợ
            if hasattr(self._view, "update_ccd1_status"):
                try:
                    self._view.update_ccd1_status("streaming")
                except Exception:
                    pass

            self._view.show_message(f"CCD1 started (camera_id={camera_id})", "success")
            logger.info(f"CCD1 worker started with camera_id={camera_id}")
        except Exception as e:
            logger.error(f"Failed to start CCD1 worker: {e}", exc_info=True)
            self._view.show_message(f"Failed to start CCD1: {e}", "error")
            self._ccd1_worker = None

    def on_ccd1_stop_clicked(self):
        """Stop CCD1 QThread."""
        logger.info("CCD1 stop requested")
        if self._ccd1_worker is None:
            return

        try:
            self._ccd1_worker.stop()
            self._ccd1_worker.wait(2000)
        except Exception as e:
            logger.error(f"Error stopping CCD1 worker: {e}", exc_info=True)
        finally:
            self._ccd1_worker = None

        if hasattr(self._view, "update_ccd1_status"):
            try:
                self._view.update_ccd1_status("stopped")
            except Exception:
                pass

        self._view.show_message("CCD1 stopped", "info")
    
    def on_disconnect_clicked(self):
        """User click Disconnect"""
        logger.info("Disconnect button clicked")
        
        # Stop streaming trước nếu đang stream
        if self._state_machine.is_streaming():
            self._stop_streaming()

        # Stop CCD1 worker nếu đang chạy
        try:
            if self._ccd1_worker is not None and self._ccd1_worker.isRunning():
                logger.info("Auto-stopping CCD1 worker on disconnect...")
                self.on_ccd1_stop_clicked()
        except Exception as e:
            logger.error(f"Failed to auto-stop CCD1 on disconnect: {e}", exc_info=True)

        self._disconnect_camera()
    
    def on_start_stream_clicked(self):
        """User click Start Stream"""
        logger.info("Start stream button clicked")
        
        if not self._state_machine.can_transition_to(AppState.STREAMING):
            self._view.show_message("Cannot start streaming in current state", "warning")
            return
        
        self._start_streaming()
    
    def on_stop_stream_clicked(self):
        """User click Stop Stream"""
        logger.info("Stop stream button clicked")
        self._stop_streaming()
    
    def on_capture_clicked(self):
        """User click Capture"""
        logger.info("Capture button clicked")
        self._capture_single_frame()
    
    def on_gain_changed(self, gain_value: int):
        """User thay đổi gain slider"""
        logger.info(f"Gain changed to: {gain_value}")
        
        # Chỉ set gain khi camera đã connected
        if not self._state_machine.is_connected():
            logger.warning("Cannot set gain: camera not connected")
            return
        
        # Set gain parameter
        if self._camera_service.set_parameter('Gain', gain_value):
            logger.info(f"Gain set to {gain_value}")
        else:
            logger.error(f"Failed to set gain to {gain_value}")
            self._view.show_message(f"Failed to set gain", "warning")
    
    def on_qr_enabled_changed(self, enabled: bool):
        """User thay đổi QR detection enable/disable"""
        logger.info(f"QR detection {'enabled' if enabled else 'disabled'}")
        self._qr_enabled = enabled
        
        if self._qr_service is None:
            logger.warning("QR service not available")
            self._view.show_message("QR service not configured", "warning")
            return
    
    # ========== Running Mode Handlers ==========
    
    def on_load_template_clicked(self, template_name: str):
        """Load a template (used by both Running Mode and Template Mode)."""
        logger.info(f"Load template: {template_name}")
        
        template = self._template_service.load_template(template_name)
        if template:
            self._template_service.set_current_template(template)
            self._view.update_current_template_info(self._build_template_info(template))
            # Ensure Template Mode shows the right panels when a template is loaded (auto-load from combo)
            if hasattr(self._view, "_set_template_tab_mode"):
                try:
                    self._view._set_template_tab_mode("browse")
                except Exception:
                    pass
            # Update region editor list (Template Mode)
            if hasattr(self._view, "update_template_regions_table"):
                self._view.update_template_regions_table(template.crop_regions)
            self._view.show_message(f"Template '{template_name}' loaded", "success")
        else:
            self._view.show_message(f"Failed to load template '{template_name}'", "error")

    def _build_template_info(self, template: Template) -> str:
        info = f"Template: {template.name}\n"
        info += f"{template.description}\n"
        info += f"Crop regions: {len(template.crop_regions)}\n"
        barcode_count = sum(1 for r in template.crop_regions if r.scan_barcode)
        info += f"Barcode regions: {barcode_count}\n"
        info += f"Image size: {template.master_image_width}x{template.master_image_height}"
        return info

    def on_current_template_region_added(self, name: str, x: int, y: int, width: int, height: int, scan_barcode: bool = True):
        """Add a new region to the currently loaded template (Template Mode editor)."""
        template = self._template_service.get_current_template()
        if template is None:
            self._view.show_message("Please load a template first", "warning")
            return

        try:
            template.crop_regions.append(CropRegion(
                name=name, x=x, y=y, width=width, height=height,
                enabled=True, scan_barcode=scan_barcode
            ))

            if self._template_service.save_template(template):
                # Keep current template in memory updated
                self._template_service.set_current_template(template)
                self._view.update_current_template_info(self._build_template_info(template))
                if hasattr(self._view, "update_template_regions_table"):
                    self._view.update_template_regions_table(template.crop_regions)
                self._view.show_message(f"Region '{name}' added", "success")
            else:
                self._view.show_message("Failed to save template after adding region", "error")
        except Exception as e:
            logger.error(f"Failed to add region to current template: {e}", exc_info=True)
            self._view.show_message(f"Error adding region: {e}", "error")

    def on_current_template_region_updated(self, index: int, x: int, y: int, width: int, height: int, scan_barcode: bool = True):
        """Update ROI of an existing region in the currently loaded template."""
        template = self._template_service.get_current_template()
        if template is None:
            self._view.show_message("Please load a template first", "warning")
            return

        if index < 0 or index >= len(template.crop_regions):
            self._view.show_message("Invalid region selected", "warning")
            return

        try:
            region = template.crop_regions[index]
            region.x = int(x)
            region.y = int(y)
            region.width = int(width)
            region.height = int(height)
            region.scan_barcode = bool(scan_barcode)

            if self._template_service.save_template(template):
                self._template_service.set_current_template(template)
                self._view.update_current_template_info(self._build_template_info(template))
                if hasattr(self._view, "update_template_regions_table"):
                    self._view.update_template_regions_table(template.crop_regions)
                self._view.show_message(f"Region '{region.name}' updated", "success")
            else:
                self._view.show_message("Failed to save template after updating region", "error")
        except Exception as e:
            logger.error(f"Failed to update region in current template: {e}", exc_info=True)
            self._view.show_message(f"Error updating region: {e}", "error")

    def on_current_template_region_deleted(self, index: int):
        """Delete a region from the currently loaded template."""
        template = self._template_service.get_current_template()
        if template is None:
            self._view.show_message("Please load a template first", "warning")
            return

        if index < 0 or index >= len(template.crop_regions):
            self._view.show_message("Invalid region selected", "warning")
            return

        try:
            region_name = template.crop_regions[index].name
            template.crop_regions.pop(index)

            if self._template_service.save_template(template):
                self._template_service.set_current_template(template)
                self._view.update_current_template_info(self._build_template_info(template))
                if hasattr(self._view, "update_template_regions_table"):
                    self._view.update_template_regions_table(template.crop_regions)
                self._view.show_message(f"Region '{region_name}' deleted", "success")
            else:
                self._view.show_message("Failed to save template after deleting region", "error")
        except Exception as e:
            logger.error(f"Failed to delete region in current template: {e}", exc_info=True)
            self._view.show_message(f"Error deleting region: {e}", "error")
    
    def on_refresh_templates_clicked(self):
        """User click Refresh Templates (Running Mode)"""
        logger.info("Refresh templates clicked (Running Mode)")
        templates = self._template_service.list_templates()
        self._view.update_template_list(templates)
        self._view.show_message(f"Found {len(templates)} template(s)", "info")
    
    def on_test_image_loaded(self, image: np.ndarray, file_path: str):
        """User loaded a test image for QR detection (Running Mode)"""
        logger.info(f"Test image loaded from file: {file_path}")
        
        # Save test image
        self._test_image = image.copy()
        self._test_image_path = file_path
        
        self._view.show_message(f"Test image loaded successfully", "info")
        logger.info("Test image ready for processing")
    
    def on_process_test_image_clicked(self):
        """User click Process Test Image - run barcode detection with template"""
        logger.info("Process test image clicked")
        
        # Validate
        if self._test_image is None:
            self._view.show_message("Please load a test image first", "warning")
            return
        
        current_template = self._template_service.get_current_template()
        if current_template is None:
            self._view.show_message("Please load a template first", "warning")
            return
        
        # Process image with template
        try:
            display_frame = self._test_image.copy()
            
            # Draw template regions on image
            show_regions = self._view.get_show_regions_enabled()
            
            if show_regions:
                display_frame = self._template_service.draw_template_regions(
                    display_frame, current_template, 
                    draw_regions=show_regions
                )
            
            # Process with template: crop regions + scan barcodes
            results = self._template_service.process_image_with_template(
                self._test_image, current_template
            )
            
            if results['success']:
                # Display cropped images and barcode results
                barcode_results = results.get('barcodes', {})
                
                # Update barcode results display
                self._view.update_barcode_results(barcode_results)
                
                # Log results
                log_text = ""
                for region_name, barcode_list in barcode_results.items():
                    if barcode_list:
                        for barcode_data in barcode_list:
                            log_text += f"[OK] {region_name}: {barcode_data}\n"
                    else:
                        log_text += f"[NG] {region_name}: No barcode found\n"
                
                if log_text:
                    logger.info(f"Barcode detection results:\n{log_text}")
                
                # Display processed image
                self._view.display_image(display_frame)
                self._view.show_message("Image processed successfully", "success")
            else:
                error_msg = results.get('error', 'Unknown error')
                self._view.show_message(f"Processing failed: {error_msg}", "error")
                logger.error(f"Template processing failed: {error_msg}")
            
        except Exception as e:
            logger.error(f"Failed to process test image: {e}", exc_info=True)
            self._view.show_message(f"Error: {str(e)}", "error")
            logger.error(f"Test image processing failed - image shape: {self._test_image.shape if self._test_image is not None else 'None'}, template: {current_template.name if current_template else 'None'}")

    def on_manual_start_clicked(self):
        """
        User click Manual Start (Running Mode)
        - Chụp 1 frame từ camera
        - Xử lý với template hiện tại
        - Hiển thị kết quả lên Barcode Results
        """
        logger.info("Manual Start (capture + process) clicked")

        # Validate camera state
        if not (self._state_machine.is_connected() or self._state_machine.is_streaming()):
            self._view.show_message("Camera is not connected", "warning")
            logger.warning("Manual start requested but camera is not connected")
            return

        # Validate template
        current_template = self._template_service.get_current_template()
        if current_template is None:
            self._view.show_message("Please load a template first", "warning")
            logger.warning("Manual start requested but no template is loaded")
            return

        try:
            # Capture single frame from camera
            frame = self._camera_service.get_frame(timeout_ms=1000)

            if frame is None:
                self._view.show_message("Failed to capture frame", "error")
                logger.warning("Manual start: failed to get frame from camera")
                return

            # Save captured image to screenccd folder
            saved_path = self._save_captured_image(frame)
            if saved_path:
                logger.info(f"Image saved to: {saved_path}")

            display_frame = frame.copy()

            # Process with template: crop regions + scan barcodes
            results = self._template_service.process_image_with_template(
                frame, current_template
            )

            if results["success"]:
                # Draw template regions on image if enabled
                if self._view.get_show_regions_enabled():
                    display_frame = self._template_service.draw_template_regions(
                        display_frame, current_template, draw_regions=True
                    )

                # Update barcode results
                barcode_results = results.get("barcodes", {})
                self._view.update_barcode_results(barcode_results)

                # Display processed image
                self._view.display_image(display_frame)
                self._view.show_message(
                    "Manual capture processed successfully", "success"
                )

                # Optional logging
                log_text = ""
                for region_name, barcode_list in barcode_results.items():
                    if barcode_list:
                        for barcode_data in barcode_list:
                            log_text += f"[OK] {region_name}: {barcode_data}\n"
                    else:
                        log_text += f"[NG] {region_name}: No barcode found\n"
                if log_text:
                    logger.info(f"Manual barcode detection results:\n{log_text}")
                
                # Gửi kết quả scan đến server
                self._send_scan_result_to_server(barcode_results)
            else:
                error_msg = results.get("error", "Unknown error")
                self._view.show_message(f"Processing failed: {error_msg}", "error")
                logger.error(f"Manual template processing failed: {error_msg}")

        except Exception as e:
            logger.error(f"Manual capture + process failed: {e}", exc_info=True)
            self._view.show_message(f"Error: {str(e)}", "error")

    # ========== CCD1 frame callback ==========

    def _on_ccd1_frame_captured(self, frame: np.ndarray):
        """
        Nhận frame từ CCD1 (QThread) và xử lý:
        - Dùng chung pipeline template/barcode như CCD2
        - Hiển thị lên vùng image CCD1 trên UI
        """
        try:
            display_frame, barcode_results = self._process_frame_with_template(frame)

            # Hiển thị lên CCD1 view nếu UI có
            if hasattr(self._view, "display_ccd1_image"):
                try:
                    self._view.display_ccd1_image(display_frame)
                except Exception as e:
                    logger.error(f"Failed to display CCD1 image: {e}", exc_info=True)

            # Gửi kết quả scan đến server (nếu có barcode)
            if barcode_results:
                self._send_scan_result_to_server(barcode_results)

        except Exception as e:
            logger.error(f"Error handling CCD1 frame: {e}", exc_info=True)
    
    # ========== Template Mode Handlers ==========
    
    def on_template_image_loaded(self, image: np.ndarray, file_path: str):
        """User loaded an image for template creation"""
        logger.info(f"Template image loaded from file: {file_path}")
        
        # Save as master image for template mode
        self._template_master_image = image.copy()
        
        # Clear previous regions
        self._template_crop_regions = []
        
        self._view.show_message(f"Template image loaded successfully", "info")
        logger.info("Template master image set")
    
    def on_template_crop_region_added(self, name: str, x: int, y: int, width: int, height: int, scan_barcode: bool = True):
        """User added a crop region (có thể có scan barcode)"""
        logger.info(f"Region added: {name} ({x}, {y}, {width}x{height}), scan_barcode={scan_barcode}")
        
        if self._template_master_image is None:
            self._view.show_message("Please load a master image first", "warning")
            return
        
        # Create crop region với scan_barcode option
        crop_region = CropRegion(name=name, x=x, y=y, width=width, height=height, scan_barcode=scan_barcode)
        self._template_crop_regions.append(crop_region)
        
        # Update view
        self._update_template_regions_display()
        logger.info(f"Regions total: {len(self._template_crop_regions)}")
    
    def _update_template_regions_display(self):
        """Update template regions list display"""
        text = ""
        
        if self._template_crop_regions:
            text += "=== Regions ===\n"
            for i, region in enumerate(self._template_crop_regions):
                scan_text = "Crop+Barcode" if region.scan_barcode else "Crop only"
                text += f"{i+1}. {region.name}: ({region.x}, {region.y}, {region.width}x{region.height}) [{scan_text}]\n"
        
        if not text:
            text = "No regions defined"
        
        self._view.update_template_regions_list(text.strip())
    
    def on_save_template_clicked(self, template_name: str, template_desc: str):
        """User click Save Template"""
        logger.info(f"Save template clicked: {template_name}")
        
        # Validate
        if self._template_master_image is None:
            self._view.show_message("Please load a master image first", "warning")
            return
        
        if not self._template_crop_regions:
            self._view.show_message("Please add at least one crop region", "warning")
            return
        
        # Create template
        h, w = self._template_master_image.shape[:2]
        template = Template(
            name=template_name,
            description=template_desc,
            crop_regions=self._template_crop_regions.copy(),
            master_image_width=w,
            master_image_height=h
        )
        
        # Save template
        if self._template_service.save_template(template):
            self._view.show_message(f"Template '{template_name}' saved successfully", "success")
            
            # Clear state
            self._template_master_image = None
            self._template_crop_regions = []
            self._view.update_template_regions_list("No regions defined")
            
            # Refresh template list
            templates = self._template_service.list_templates()
            self._view.update_template_list(templates)
            logger.info(f"Template list refreshed, total: {len(templates)}")
        else:
            self._view.show_message("Failed to save template", "error")
    
    
    def on_template_test_image_loaded(self, image: np.ndarray, file_path: str):
        """User loaded a test image for template processing"""
        logger.info(f"Template test image loaded from file: {file_path}")
        
        # Save test image
        self._template_test_image = image.copy()
        
        self._view.show_message(f"Test image loaded successfully", "info")
        logger.info("Template test image ready for processing")
    
    def on_process_template_clicked(self):
        """User click Process Template - crop regions + scan barcodes"""
        logger.info("Process template clicked")
        
        # Validate
        if self._template_test_image is None:
            self._view.show_message("Please load a test image first", "warning")
            logger.warning("Template processing requested but no test image loaded")
            return
        
        current_template = self._template_service.get_current_template()
        if current_template is None:
            self._view.show_message("Please load a template first", "warning")
            logger.warning("Template processing requested but no template loaded")
            return
        
        # Process image
        try:
            logger.info("Starting template processing with test image")
            display_frame = self._template_test_image.copy()
            
            # Draw template regions on image
            show_regions = self._view.get_show_regions_enabled()
            
            if show_regions:
                display_frame = self._template_service.draw_template_regions(
                    display_frame, current_template, 
                    draw_regions=show_regions
                )
            
            # Process with template
            logger.info("Running process_image_with_template")
            results = self._template_service.process_image_with_template(
                self._template_test_image, current_template
            )
            
            if results['success']:
                # Format results text
                results_text = ""
                
                # Cropped images
                cropped_images = results.get('cropped_images', {})
                if cropped_images:
                    results_text += "=== Cropped Images ===\n"
                    for name, img in cropped_images.items():
                        h, w = img.shape[:2]
                        results_text += f"{name}: {w}x{h}\n"
                        # logger.info(f"{name}: {w}x{h}")
                
                # Barcodes
                barcodes = results.get('barcodes', {})
                if barcodes:
                    results_text += "\n=== Barcodes ===\n"
                    for region_name, barcode_list in barcodes.items():
                        if barcode_list:
                            for barcode_data in barcode_list:
                                results_text += f"{region_name}: {barcode_data}\n"
                                logger.info(f"{region_name}: {barcode_data}")
                        else:
                            results_text += f"{region_name}: No barcode detected\n"
                            logger.info(f"{region_name}: No barcode detected")
                
                if not results_text:
                    results_text = "No results"

                logger.info("Template processing succeeded")
                self._view.update_template_results(results_text.strip())
                self._view.show_message("Template processing completed", "success")
                
                # Gửi kết quả scan đến server
                if barcodes:
                    self._send_scan_result_to_server(barcodes)
            else:
                error_msg = results.get('error', 'Unknown error')
                logger.warning(f"Template processing returned error: {error_msg}")
                self._view.update_template_results(f"Error: {error_msg}")
                self._view.show_message(f"Processing failed: {error_msg}", "error")
            
            # Display result image
            self._view.display_image(display_frame)
            
        except Exception as e:
            logger.error(f"Error processing template: {e}", exc_info=True)
            self._view.show_message(f"Error processing template: {e}", "error")
    
    # ========== Private Methods ==========
    
    def _get_screenccd_directory(self) -> str:
        """Get screenccd directory for saving captured images"""
        # Use current working directory or create screenccd folder there
        base_path = os.getcwd()
        screenccd_dir = os.path.join(base_path, "screenccd")
        return screenccd_dir
    
    def _save_captured_image(self, image: np.ndarray) -> Optional[str]:
        """
        Save captured image to screenccd folder with timestamp
        
        Args:
            image: Image to save (numpy array)
        
        Returns:
            File path if successful, None otherwise
        """
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            filename = f"ccd_{timestamp}.png"
            filepath = os.path.join(self._screenccd_dir, filename)
            
            # Save image
            cv2.imwrite(filepath, image)
            logger.info(f"Captured image saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save captured image: {e}", exc_info=True)
            return None
    
    def _connect_camera(self):
        """Kết nối MindVision camera"""
        try:
            # Transition to CONNECTING
            if not self._state_machine.transition_to(AppState.CONNECTING):
                return
            
            self._view.update_status("connecting")
            self._view.show_message("Connecting to MindVision camera...", "info")
            
            # Lấy config từ YAML
            # Ưu tiên key mới `camera_ccd2` (tách biệt với `camera_ccd1`).
            # Nếu project cũ vẫn còn dùng key `camera`, sẽ fallback cho backwards-compat.
            camera_config = (
                self._settings.get('camera_ccd2')
                or self._settings.get('camera')
                or {}
            )
            camera_id = camera_config.get('ip', 'cam2')  # Default: cam2
            
            logger.info(f"Connecting to MindVision camera: {camera_id}")
            
            # Tạo camera instance
            if not self._camera_service.create_camera(camera_id, camera_config):
                raise Exception("Failed to create camera instance")
            
            # Connect
            if not self._camera_service.connect():
                raise Exception("Failed to connect to camera")
            
            # Transition to CONNECTED
            self._state_machine.transition_to(AppState.CONNECTED)
            
            # Update view
            camera_info = self._camera_service.get_camera_info()
            self._view.update_camera_info(camera_info)
            
            # Load saved camera settings and apply
            saved_settings = self._camera_settings_service.load_settings()
            if saved_settings:
                logger.info("Applying saved camera settings...")
                # Update UI controls
                self._view.update_camera_settings_controls(saved_settings)
                # Update ranges if available
                self._apply_camera_ranges()
                # Apply to camera
                if 'exposure_time' in saved_settings:
                    self._camera_service.set_parameter('ExposureTime', saved_settings['exposure_time'])
                if 'gain' in saved_settings:
                    self._camera_service.set_parameter('Gain', saved_settings['gain'])
                if 'brightness' in saved_settings:
                    self._camera_service.set_parameter('Gamma', saved_settings['brightness'])
                if 'contrast' in saved_settings:
                    self._camera_service.set_parameter('Contrast', saved_settings['contrast'])
                if 'saturation' in saved_settings:
                    self._camera_service.set_parameter('Saturation', saved_settings['saturation'])
                logger.info("Saved camera settings applied")
            else:
                # No saved settings → pull current camera defaults and reflect to UI
                defaults = self._get_camera_default_settings()
                if defaults:
                    logger.info("Loaded camera defaults (no saved settings), updating UI")
                    self._view.update_camera_settings_controls(defaults)
                    self._apply_camera_ranges()
            
            self._view.show_message("Camera connected successfully", "success")

            # Auto-start streaming right after successful connection
            try:
                logger.info("Auto-start streaming after connect")
                self._start_streaming()
            except Exception as auto_stream_err:
                logger.error(f"Auto-start streaming failed: {auto_stream_err}", exc_info=True)
                # Keep connected state; inform user
                self._view.show_message(f"Connected but failed to start stream: {auto_stream_err}", "warning")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            self._state_machine.transition_to(AppState.ERROR)
            self._view.show_message(f"Connection failed: {e}", "error")
            # Update camera info to disconnected state
            try:
                camera_info = self._camera_service.get_camera_info()
                if camera_info:
                    camera_info['is_connected'] = False
                    camera_info['is_grabbing'] = False
                    self._view.update_camera_info(camera_info)
            except Exception as update_error:
                logger.error(f"Failed to update camera info: {update_error}")
            self._state_machine.reset()
    
    def _disconnect_camera(self):
        """Ngắt kết nối camera"""
        try:
            logger.info("Disconnecting camera...")
            
            # Disconnect
            self._camera_service.disconnect()
            
            # Reset state
            self._state_machine.reset()
            
            # Update view
            self._view.show_message("Camera disconnected", "info")
            
        except Exception as e:
            logger.error(f"Disconnect failed: {e}", exc_info=True)
            self._view.show_message(f"Disconnect failed: {e}", "error")
    
    def _start_streaming(self):
        """Bắt đầu streaming"""
        try:
            logger.info("Starting streaming...")
            
            # Start grabbing
            if not self._camera_service.start_streaming():
                raise Exception("Failed to start streaming")
            
            # Transition to STREAMING
            if not self._state_machine.transition_to(AppState.STREAMING):
                self._camera_service.stop_streaming()
                return
            
            # Start timer để lấy frame liên tục
            self._stream_timer.start(self._stream_interval)
            
            self._view.show_message("Streaming started", "success")
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}", exc_info=True)
            self._view.show_message(f"Failed to start streaming: {e}", "error")
    
    def _stop_streaming(self):
        """Dừng streaming"""
        try:
            logger.info("Stopping streaming...")
            
            # Stop timer
            self._stream_timer.stop()
            
            # Stop grabbing
            self._camera_service.stop_streaming()
            
            # Transition back to CONNECTED
            self._state_machine.transition_to(AppState.CONNECTED)
            
            self._view.show_message("Streaming stopped", "info")
            
        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}", exc_info=True)
            self._view.show_message(f"Failed to stop streaming: {e}", "error")
    
    def _on_stream_timer(self):
        """Timer callback - lấy frame và hiển thị"""
        try:
            # Get frame
            frame = self._camera_service.get_frame(timeout_ms=100)
            
            if frame is not None:
                # Cache latest camera frame (already flipped in camera service if enabled)
                try:
                    self._last_camera_frame = frame.copy()
                except Exception:
                    self._last_camera_frame = frame

                # Dùng chung pipeline xử lý template/barcode
                display_frame, _ = self._process_frame_with_template(frame)

                # Display frame cho CCD2 (camera hiện tại)
                self._view.display_image(display_frame)
            else:
                logger.warning("Failed to get frame")
                
        except Exception as e:
            logger.error(f"Error in stream timer: {e}", exc_info=True)
            # Không stop streaming ngay, cho phép retry

    # ========== Shared processing helper (CCD1 & CCD2) ==========

    def _process_frame_with_template(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Xử lý frame với template:
        - Crop regions + scan barcode
        - Vẽ ROI nếu được bật
        - Update barcode_results lên view

        Returns:
            (display_frame, barcode_results)
        """
        display_frame = frame.copy()
        barcode_results: Dict[str, Any] = {}

        try:
            current_template = self._template_service.get_current_template()

            if self._barcode_enabled and current_template is not None:
                results = self._template_service.process_image_with_template(
                    frame, current_template
                )

                if results.get("success"):
                    # Draw template regions if enabled
                    if self._view.get_show_regions_enabled():
                        display_frame = self._template_service.draw_template_regions(
                            display_frame, current_template, draw_regions=True
                        )

                    barcode_results = results.get("barcodes", {}) or {}

                    # Update barcode results display
                    self._view.update_barcode_results(barcode_results)

                    # Log chi tiết (debug)
                    for region_name, barcode_list in barcode_results.items():
                        if barcode_list:
                            for barcode_data in barcode_list:
                                logger.debug(
                                    f"DataMatrix found in '{region_name}': {barcode_data}"
                                )
                else:
                    error_msg = results.get("error", "Unknown error")
                    logger.warning(
                        f"Template processing failed in streaming: {error_msg}"
                    )
        except Exception as e:
            logger.error(f"Error in _process_frame_with_template: {e}", exc_info=True)

        return display_frame, barcode_results

    def _on_remote_message(self, msg: str):
        """Handle incoming messages from TCP server (if needed)."""
        logger.debug(f"Received message from server: {msg}")
        # Có thể xử lý các lệnh từ server ở đây nếu cần
    
    def _get_first_serial_number(self, barcode_results: dict) -> str:
        """
        Lấy mã serial number đầu tiên từ Region_1 (nếu có), 
        nếu không có thì lấy từ region đầu tiên có barcode
        
        Args:
            barcode_results: Dict với key là region_name, value là list barcode_data
            
        Returns:
            Mã serial number đầu tiên, hoặc "" nếu không có
        """
        if not barcode_results:
            return ""
        
        # Ưu tiên lấy từ Region_1
        if "Region_1" in barcode_results:
            region_1_barcodes = barcode_results["Region_1"]
            if region_1_barcodes and len(region_1_barcodes) > 0:
                return region_1_barcodes[0]
        
        # Nếu không có Region_1, lấy từ region đầu tiên có barcode
        # Sắp xếp theo tên region để đảm bảo thứ tự
        sorted_regions = sorted(barcode_results.items())
        
        for region_name, barcode_list in sorted_regions:
            if barcode_list and len(barcode_list) > 0:
                # Lấy mã đầu tiên từ region đầu tiên có barcode
                return barcode_list[0]
        
        return ""
    
    def _check_all_regions_scanned(self, barcode_results: dict) -> bool:
        """
        Kiểm tra xem tất cả các region có scan được barcode không
        
        Args:
            barcode_results: Dict với key là region_name, value là list barcode_data
            
        Returns:
            True nếu tất cả region đều có barcode, False nếu có region nào không có
        """
        if not barcode_results:
            return False
        
        for region_name, barcode_list in barcode_results.items():
            if not barcode_list or len(barcode_list) == 0:
                return False
        
        return True
    
    def _send_scan_result_to_server(self, barcode_results: dict):
        """
        Gửi kết quả scan đến server:
        - Nếu scan được tất cả các vùng: gửi "OK,<mã_đầu_tiên>"
        - Nếu không scan được: gửi "FAIL,<mã_đầu_tiên>"
        
        Args:
            barcode_results: Dict với key là region_name, value là list barcode_data
        """
        if not self._remote_client.is_connected():
            return
        
        # Lấy mã đầu tiên từ region đầu tiên
        first_sn = self._get_first_serial_number(barcode_results)
        
        if not first_sn:
            # Không có mã nào, gửi FAIL không có SN
            self._remote_client.send_fail("")
            logger.info("Sent FAIL to TCP server (no barcode found)")
            return
        
        # Kiểm tra xem tất cả các region có scan được không
        all_scanned = self._check_all_regions_scanned(barcode_results)
        
        if all_scanned:
            # Tất cả đều scan được → gửi OK,SN
            self._remote_client.send_ok(first_sn)
            logger.info(f"Sent OK,{first_sn} to TCP server (all regions scanned)")
        else:
            # Có region không scan được → gửi FAIL,SN
            self._remote_client.send_fail(first_sn)
            logger.info(f"Sent FAIL,{first_sn} to TCP server (some regions not scanned)")
    
    def _capture_single_frame(self):
        """Chụp một frame đơn"""
        try:
            logger.info("Capturing single frame...")
            
            frame = self._camera_service.get_frame(timeout_ms=1000)
            
            if frame is not None:
                # Save as master image for teaching mode
                self._teaching_master_image = frame.copy()
                
                # Save captured image to screenccd folder
                saved_path = self._save_captured_image(frame)
                if saved_path:
                    logger.info(f"Image saved to: {saved_path}")
                
                self._view.display_image(frame)
                self._view.show_message("Frame captured (saved as master image)", "success")
                logger.info("Master image captured for teaching mode")
                
                # Gửi tín hiệu OK đến server sau khi CCD capture hoàn tất
                if self._remote_client.is_connected():
                    self._remote_client.send_ok()
                    logger.info("Sent OK signal to TCP server after CCD capture")
            else:
                self._view.show_message("Failed to capture frame", "error")
                
        except Exception as e:
            logger.error(f"Capture failed: {e}", exc_info=True)
            self._view.show_message(f"Capture failed: {e}", "error")
    
    def _detect_qr_with_recipe(self, frame, recipe: Recipe, match_result: MatchResult):
        """
        Detect QR codes using recipe with transformed ROIs
        
        Args:
            frame: Input frame
            recipe: Current recipe
            match_result: Template matching result
        
        Returns:
            List of QRDetectionResult
        """
        if self._qr_service is None:
            return []
        
        # Temporarily update QR service ROI regions based on recipe + offset
        # Transform QR ROIs based on template match offset
        transformed_rois = []
        for qr_roi in recipe.qr_roi_regions:
            if not qr_roi.enabled:
                continue
            
            # Get absolute coordinates with offset
            abs_x, abs_y, w, h = qr_roi.get_absolute_coords(
                match_result.x,
                match_result.y
            )
            
            # Create temporary ROI for QR service
            from app.model.qr.qr_detection_service import ROIRegion
            temp_roi = ROIRegion(
                name=qr_roi.name,
                enabled=True,
                x=abs_x,
                y=abs_y,
                width=w,
                height=h,
                use_percentage=False
            )
            transformed_rois.append(temp_roi)
        
        # Backup original ROIs
        original_rois = self._qr_service.roi_regions
        
        # Set transformed ROIs
        self._qr_service.roi_regions = transformed_rois
        
        # Detect QR codes
        qr_results = self._qr_service.detect_qr_codes(frame)
        
        # Restore original ROIs
        self._qr_service.roi_regions = original_rois
        
        return qr_results
    
    def on_barcode_enabled_changed(self, enabled: bool):
        """User toggled barcode detection"""
        logger.info(f"Barcode detection enabled: {enabled}")
        # Barcode detection is always enabled when template is loaded
        # This is just for UI state
        pass
    
    def _append_qr_log(self, message: str):
        """Append log message to QR results text box (deprecated, use barcode results)"""
        try:
            # Get current text
            current_text = self._view.txt_barcode_results.toPlainText()
            
            # Append new message with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_line = f"[{timestamp}] {message}"
            
            # Limit log size (keep last 100 lines)
            lines = current_text.split('\n')
            if len(lines) > 100:
                lines = lines[-100:]
            
            lines.append(log_line.strip())
            new_text = '\n'.join(lines)
            
            self._view.txt_barcode_results.setPlainText(new_text)
            
            # Auto scroll to bottom
            scrollbar = self._view.txt_barcode_results.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            logger.error(f"Error appending QR log: {e}", exc_info=True)
    
    # ========== Camera Settings Handlers ==========
    
    def on_camera_parameter_changed(self, param_name: str, value: Any):
        """User changed camera parameter"""
        logger.info(f"Camera parameter changed: {param_name} = {value}")
        
        # Map parameter names
        param_map = {
            'ExposureTime': 'ExposureTime',
            'Gain': 'Gain',
            'Gamma': 'Gamma',
            'Contrast': 'Contrast',
            'Saturation': 'Saturation'
        }
        
        if param_name in param_map:
            success = self._camera_service.set_parameter(param_map[param_name], value)
            if success:
                logger.info(f"Camera parameter {param_name} set to {value}")
            else:
                logger.warning(f"Failed to set camera parameter {param_name}")
    
    def on_save_camera_settings(self, settings: Dict[str, Any]) -> bool:
        """User clicked Save Settings"""
        logger.info("Saving camera settings")
        # Include current camera ranges (for reference) if available
        ranges = self._get_camera_param_ranges()
        if ranges:
            settings = {**settings, **ranges}
        
        # Save to AppData
        success = self._camera_settings_service.save_settings(settings)
        
        if success:
            logger.info("Camera settings saved successfully")
            self._view.show_message("Settings saved successfully", "success")
        else:
            logger.error("Failed to save camera settings")
            self._view.show_message("Failed to save settings", "error")
        
        return success
    
    def on_load_camera_settings(self) -> Optional[Dict[str, Any]]:
        """User clicked Load Settings"""
        logger.info("Loading camera settings")
        
        # Load from AppData
        settings = self._camera_settings_service.load_settings()
        
        if settings:
            # Update UI controls
            self._view.update_camera_settings_controls(settings)
            # Apply ranges from settings (in case camera not connected)
            if hasattr(self._view, "update_camera_setting_ranges"):
                ranges = {
                    'exposure_time_range': settings.get('exposure_time_range'),
                    'gain_range': settings.get('gain_range'),
                    'brightness_range': settings.get('brightness_range'),
                    'contrast_range': settings.get('contrast_range'),
                    'saturation_range': settings.get('saturation_range'),
                }
                self._view.update_camera_setting_ranges(ranges)
            self._apply_camera_ranges()
            
            # Apply settings to camera if connected
            if self._camera_service.is_connected():
                if 'exposure_time' in settings:
                    self._camera_service.set_parameter('ExposureTime', settings['exposure_time'])
                if 'gain' in settings:
                    self._camera_service.set_parameter('Gain', settings['gain'])
                if 'brightness' in settings:
                    self._camera_service.set_parameter('Gamma', settings['brightness'])
                if 'contrast' in settings:
                    self._camera_service.set_parameter('Contrast', settings['contrast'])
                if 'saturation' in settings:
                    self._camera_service.set_parameter('Saturation', settings['saturation'])
            
            logger.info("Camera settings loaded successfully")
            self._view.show_message("Settings loaded successfully", "success")
        else:
            # Fallback: read current camera parameters as defaults
            defaults = self._get_camera_default_settings()
            if defaults:
                logger.info("No saved settings; using camera defaults")
                self._view.update_camera_settings_controls(defaults)
                self._apply_camera_ranges()
                self._view.show_message("Loaded defaults from camera", "info")
            else:
                logger.info("No saved settings found")
                self._view.show_message("No saved settings found", "info")
        
        return settings

    def _get_camera_default_settings(self) -> Dict[str, Any]:
        """Get current camera parameters as defaults when no saved settings exist."""
        if not self._camera_service.is_connected():
            return {}

        params = {
            'exposure_time': self._camera_service.get_parameter('ExposureTime'),
            'gain': self._camera_service.get_parameter('Gain'),
            'brightness': self._camera_service.get_parameter('Gamma'),
            'contrast': self._camera_service.get_parameter('Contrast'),
            'saturation': self._camera_service.get_parameter('Saturation'),
        }
        # Remove None entries
        return {k: v for k, v in params.items() if v is not None}

    def _get_camera_param_ranges(self) -> Dict[str, Any]:
        """Get parameter ranges from camera if available."""
        if not self._camera_service.is_connected():
            return {}
        ranges = {
            'exposure_time_range': self._camera_service.get_parameter_range('ExposureTime'),
            'gain_range': self._camera_service.get_parameter_range('Gain'),
            'brightness_range': self._camera_service.get_parameter_range('Gamma'),
            'contrast_range': self._camera_service.get_parameter_range('Contrast'),
            'saturation_range': self._camera_service.get_parameter_range('Saturation'),
        }
        return {k: v for k, v in ranges.items() if v is not None}

    def _apply_camera_ranges(self):
        """Push camera parameter ranges to view if available."""
        ranges = self._get_camera_param_ranges()
        if ranges and hasattr(self._view, "update_camera_setting_ranges"):
            try:
                self._view.update_camera_setting_ranges(ranges)
            except Exception as e:
                logger.error(f"Failed to apply camera ranges: {e}", exc_info=True)
    
    def _on_state_changed(self, old_state: AppState, new_state: AppState):
        """Callback khi state thay đổi"""
        logger.info(f"State changed: {old_state.value} -> {new_state.value}")
        
        # Update view based on new state
        self._view.update_status(new_state.value)
        
        # Update camera info
        if self._camera_service.is_connected():
            camera_info = self._camera_service.get_camera_info()
            self._view.update_camera_info(camera_info)

