"""
Camera Test Presenter - Điều khiển test camera từng bước
Mỗi step độc lập, có thể test riêng biệt
"""
import logging
from PySide6.QtCore import QObject
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class CameraTestPresenter(QObject):
    """
    Camera Test Presenter - Test camera step by step
    
    Quản lý trạng thái và điều khiển từng bước kết nối camera
    """
    
    def __init__(self, view):
        super().__init__()
        self._view = view
        
        # Camera components
        self._mvsdk = None
        self._device_list = []
        self._selected_device = None
        self._camera_handle = None
        self._camera_cap = None
        self._frame_buffer = None
        self._is_grabbing = False
        self._mono_camera = False
        
        # Connect signals
        self._view.sig_step1_clicked.connect(self._on_step1_load_sdk)
        self._view.sig_step2_clicked.connect(self._on_step2_enumerate)
        self._view.sig_step3_clicked.connect(self._on_step3_init_camera)
        self._view.sig_step4_clicked.connect(self._on_step4_configure)
        self._view.sig_step5_clicked.connect(self._on_step5_start_grab)
        self._view.sig_step6_clicked.connect(self._on_step6_get_frame)
        self._view.sig_step7_clicked.connect(self._on_step7_stop_grab)
        self._view.sig_step8_clicked.connect(self._on_step8_close_camera)
        
        logger.info("CameraTestPresenter initialized")
        
        # Auto trigger step 1
        self._view.enable_step(1, True)
        self._view.append_log("Ready. Click [1] Load SDK to start.")
    
    # ========== Step Handlers ==========
    
    def _on_step1_load_sdk(self):
        """[1] Load SDK"""
        self._view.append_log("\n[1] Loading SDK...")
        
        try:
            import mvsdk
            self._mvsdk = mvsdk
            
            self._view.append_log("✓ SDK loaded successfully")
            self._view.append_log(f"  SDK location: {mvsdk.__file__}")
            
            self._view.update_step_status(1, "✓ Loaded", success=True)
            self._view.enable_step(2, True)
            
        except ImportError as e:
            self._view.append_log(f"✗ Failed to import mvsdk: {e}")
            self._view.append_log("  Make sure mvsdk.py is in project root")
            self._view.update_step_status(1, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(1, "✗ Error", success=False)
    
    def _on_step2_enumerate(self):
        """[2] Enumerate cameras"""
        if self._mvsdk is None:
            self._view.append_log("✗ SDK not loaded. Run step 1 first.")
            return
        
        self._view.append_log("\n[2] Enumerating cameras...")
        
        try:
            self._device_list = self._mvsdk.CameraEnumerateDevice()
            nDev = len(self._device_list)
            
            if nDev < 1:
                self._view.append_log("✗ No camera found")
                self._view.update_step_status(2, "✗ No camera", success=False)
                return
            
            self._view.append_log(f"✓ Found {nDev} camera(s):")
            for i, dev in enumerate(self._device_list):
                name = dev.GetFriendlyName()
                port = dev.GetPortType()
                sn = dev.GetSn()
                self._view.append_log(f"  [{i}] {name} - {port} (SN: {sn})")
            
            self._view.update_step_status(2, f"✓ Found {nDev} cam(s)", success=True)
            self._view.enable_step(3, True)
            
        except self._mvsdk.CameraException as e:
            self._view.append_log(f"✗ CameraException({e.error_code}): {e.message}")
            self._view.update_step_status(2, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(2, "✗ Error", success=False)
    
    def _on_step3_init_camera(self):
        """[3] Initialize camera (open cam2)"""
        if not self._device_list:
            self._view.append_log("✗ No cameras. Run step 2 first.")
            return
        
        self._view.append_log("\n[3] Initializing camera (cam2)...")
        
        try:
            # Select camera 2 (index 1)
            camera_index = 1  # cam2
            
            if camera_index >= len(self._device_list):
                self._view.append_log(f"✗ Camera index {camera_index} not found")
                self._view.append_log(f"  Only {len(self._device_list)} camera(s) available")
                self._view.update_step_status(3, "✗ Not found", success=False)
                return
            
            self._selected_device = self._device_list[camera_index]
            self._view.append_log(f"  Selected: [{camera_index}] {self._selected_device.GetFriendlyName()}")
            
            # Init camera
            self._camera_handle = self._mvsdk.CameraInit(self._selected_device, -1, -1)
            self._view.append_log(f"✓ Camera initialized, handle: {self._camera_handle}")
            
            # Get capability
            self._camera_cap = self._mvsdk.CameraGetCapability(self._camera_handle)
            self._mono_camera = (self._camera_cap.sIspCapacity.bMonoSensor != 0)
            
            cam_type = "MONO" if self._mono_camera else "COLOR"
            self._view.append_log(f"✓ Camera type: {cam_type}")
            
            max_res = f"{self._camera_cap.sResolutionRange.iWidthMax}x{self._camera_cap.sResolutionRange.iHeightMax}"
            self._view.append_log(f"  Max resolution: {max_res}")
            
            self._view.update_step_status(3, f"✓ Opened", success=True)
            self._view.enable_step(4, True)
            
        except self._mvsdk.CameraException as e:
            self._view.append_log(f"✗ CameraInit failed({e.error_code}): {e.message}")
            self._view.update_step_status(3, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(3, "✗ Error", success=False)
    
    def _on_step4_configure(self):
        """[4] Configure camera parameters"""
        if self._camera_handle is None:
            self._view.append_log("✗ Camera not opened. Run step 3 first.")
            return
        
        self._view.append_log("\n[4] Configuring camera...")
        
        try:
            # Set output format
            if self._mono_camera:
                self._mvsdk.CameraSetIspOutFormat(self._camera_handle, self._mvsdk.CAMERA_MEDIA_TYPE_MONO8)
                self._view.append_log("  Output format: MONO8")
            else:
                self._view.append_log("  Output format: RGB8")
            
            # Set trigger mode (0=continuous)
            self._mvsdk.CameraSetTriggerMode(self._camera_handle, 0)
            self._view.append_log("  Trigger mode: Continuous")
            
            # Set manual exposure
            exposure_time = 30000  # 30ms
            self._mvsdk.CameraSetAeState(self._camera_handle, 0)  # Manual
            self._mvsdk.CameraSetExposureTime(self._camera_handle, exposure_time)
            self._view.append_log(f"  Exposure: Manual, {exposure_time} μs ({exposure_time/1000.0:.1f} ms)")
            
            # Allocate frame buffer
            width_max = self._camera_cap.sResolutionRange.iWidthMax
            height_max = self._camera_cap.sResolutionRange.iHeightMax
            bytes_per_pixel = 1 if self._mono_camera else 3
            buffer_size = width_max * height_max * bytes_per_pixel
            
            self._frame_buffer = self._mvsdk.CameraAlignMalloc(buffer_size, 16)
            self._view.append_log(f"  Buffer allocated: {buffer_size} bytes")
            
            self._view.append_log("✓ Camera configured")
            
            self._view.update_step_status(4, "✓ Configured", success=True)
            self._view.enable_step(5, True)
            
        except self._mvsdk.CameraException as e:
            self._view.append_log(f"✗ Config failed({e.error_code}): {e.message}")
            self._view.update_step_status(4, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(4, "✗ Error", success=False)
    
    def _on_step5_start_grab(self):
        """[5] Start grabbing"""
        if self._camera_handle is None:
            self._view.append_log("✗ Camera not configured. Run steps 1-4 first.")
            return
        
        self._view.append_log("\n[5] Starting grabbing...")
        
        try:
            self._mvsdk.CameraPlay(self._camera_handle)
            self._is_grabbing = True
            
            self._view.append_log("✓ Camera is now streaming")
            
            self._view.update_step_status(5, "✓ Streaming", success=True)
            self._view.enable_step(6, True)
            self._view.enable_step(7, True)
            
        except self._mvsdk.CameraException as e:
            self._view.append_log(f"✗ CameraPlay failed({e.error_code}): {e.message}")
            self._view.update_step_status(5, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(5, "✗ Error", success=False)
    
    def _on_step6_get_frame(self):
        """[6] Get one frame"""
        if not self._is_grabbing:
            self._view.append_log("✗ Camera not streaming. Run step 5 first.")
            return
        
        self._view.append_log("\n[6] Getting frame...")
        
        pRawData = None
        
        try:
            # Get raw frame
            timeout_ms = 2000
            pRawData, FrameHead = self._mvsdk.CameraGetImageBuffer(self._camera_handle, timeout_ms)
            
            # Process frame
            self._mvsdk.CameraImageProcess(self._camera_handle, pRawData, self._frame_buffer, FrameHead)
            
            # Convert to NumPy
            width = FrameHead.iWidth
            height = FrameHead.iHeight
            
            if self._mono_camera:
                frame_data = (self._mvsdk.c_ubyte * width * height).from_address(self._frame_buffer)
                image = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width))
            else:
                frame_data = (self._mvsdk.c_ubyte * width * height * 3).from_address(self._frame_buffer)
                image = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 3))
            
            # Copy data
            image = image.copy()
            
            # Display
            self._view.display_image(image)
            
            self._view.append_log(f"✓ Frame captured: {width}x{height}")
            self._view.append_log(f"  Min: {image.min()}, Max: {image.max()}, Mean: {image.mean():.1f}")
            
            self._view.update_step_status(6, "✓ Got frame", success=True)
            
        except self._mvsdk.CameraException as e:
            if e.error_code == self._mvsdk.CAMERA_STATUS_TIME_OUT:
                self._view.append_log(f"⚠ Timeout ({timeout_ms}ms)")
            else:
                self._view.append_log(f"✗ GetImageBuffer failed({e.error_code}): {e.message}")
            self._view.update_step_status(6, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(6, "✗ Error", success=False)
        finally:
            # Release buffer
            if pRawData is not None:
                try:
                    self._mvsdk.CameraReleaseImageBuffer(self._camera_handle, pRawData)
                except:
                    pass
    
    def _on_step7_stop_grab(self):
        """[7] Stop grabbing"""
        if not self._is_grabbing:
            self._view.append_log("✗ Camera not streaming.")
            return
        
        self._view.append_log("\n[7] Stopping grabbing...")
        
        try:
            self._mvsdk.CameraPause(self._camera_handle)
            self._is_grabbing = False
            
            self._view.append_log("✓ Streaming stopped")
            
            self._view.update_step_status(7, "✓ Stopped", success=True)
            self._view.enable_step(6, False)
            self._view.enable_step(8, True)
            
        except self._mvsdk.CameraException as e:
            self._view.append_log(f"✗ CameraPause failed({e.error_code}): {e.message}")
            self._view.update_step_status(7, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(7, "✗ Error", success=False)
    
    def _on_step8_close_camera(self):
        """[8] Close camera"""
        if self._camera_handle is None:
            self._view.append_log("✗ Camera not opened.")
            return
        
        self._view.append_log("\n[8] Closing camera...")
        
        try:
            # Stop grabbing if still running
            if self._is_grabbing:
                self._mvsdk.CameraPause(self._camera_handle)
                self._is_grabbing = False
                self._view.append_log("  Streaming stopped")
            
            # Free buffer
            if self._frame_buffer is not None:
                self._mvsdk.CameraAlignFree(self._frame_buffer)
                self._frame_buffer = None
                self._view.append_log("  Buffer freed")
            
            # Uninit camera
            self._mvsdk.CameraUnInit(self._camera_handle)
            self._camera_handle = None
            self._view.append_log("  Camera uninitialized")
            
            self._view.append_log("✓ Camera closed")
            
            self._view.update_step_status(8, "✓ Closed", success=True)
            
            # Can restart from step 3
            self._view.enable_step(3, True)
            self._view.enable_step(4, False)
            self._view.enable_step(5, False)
            self._view.enable_step(6, False)
            self._view.enable_step(7, False)
            self._view.enable_step(8, False)
            
        except self._mvsdk.CameraException as e:
            self._view.append_log(f"✗ Close failed({e.error_code}): {e.message}")
            self._view.update_step_status(8, "✗ Failed", success=False)
        except Exception as e:
            self._view.append_log(f"✗ Error: {e}")
            self._view.update_step_status(8, "✗ Error", success=False)
    
    def cleanup(self):
        """Cleanup when app closes"""
        logger.info("Cleaning up...")
        
        if self._camera_handle is not None:
            try:
                if self._is_grabbing:
                    self._mvsdk.CameraPause(self._camera_handle)
                if self._frame_buffer is not None:
                    self._mvsdk.CameraAlignFree(self._frame_buffer)
                self._mvsdk.CameraUnInit(self._camera_handle)
                logger.info("Camera cleaned up")
            except:
                pass

