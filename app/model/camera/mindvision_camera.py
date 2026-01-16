import numpy as np
from typing import Optional, Dict, Any, List
from .camera_base import CameraBase
import logging

logger = logging.getLogger(__name__)


class MindVisionCamera(CameraBase):
    
    def __init__(self, camera_id: str, config: Dict[str, Any]):
        super().__init__(camera_id, config)
        self._handle = None
        self._device_info = None
        self._cap = None
        self._frame_buffer = None
        self._mono_camera = False
        
        # Import SDK từ mvsdk.py trong project
        try:
            import mvsdk
            self.mvsdk = mvsdk
            logger.info(" MindVision SDK loaded successfully (mvsdk.py)")
        except ImportError as e:
            logger.error(f"Cannot import mvsdk: {e}")
            logger.error("Make sure mvsdk.py is in project root")
            self.mvsdk = None
    
    def connect(self) -> bool:
        """
        Kết nối camera theo flow:
        [1] Load SDK → [2] Enumerate → [3] Init → [4] Config → [5] Ready
        """
        if self.mvsdk is None:
            logger.error("MindVision SDK not available")
            return False
        
        try:
            logger.info("=" * 60)
            logger.info(f"[1/5] Connecting to MindVision camera: {self.camera_id}")
            
            # [2] Enumerate devices - Quét tất cả camera
            logger.info("[2/5] Enumerating devices...")
            device_list = self._enumerate_devices()
            if not device_list:
                logger.error("No MindVision camera found")
                return False
            
            logger.info(f"Found {len(device_list)} camera(s)")
            
            # [2.1] Select camera - Chọn camera theo camera_id
            logger.info("[2.1] Selecting camera...")
            self._device_info = self._select_camera(device_list)
            if self._device_info is None:
                logger.error(f"Cannot select camera: {self.camera_id}")
                return False
            
            logger.info(f"Selected: {self._device_info.GetFriendlyName()} (SN: {self._device_info.GetSn()})")
            
            # [3] Init camera - Mở camera (tạo handle)
            logger.info("[3/5] Initializing camera...")
            self._handle = self.mvsdk.CameraInit(self._device_info, -1, -1)
            logger.info(f"Camera initialized, handle: {self._handle}")
            
            # [3.1] Get capability
            self._cap = self.mvsdk.CameraGetCapability(self._handle)
            
            # Check if mono or color camera
            self._mono_camera = (self._cap.sIspCapacity.bMonoSensor != 0)
            logger.info(f"Camera type: {'MONO' if self._mono_camera else 'COLOR'}")
            
            # [4] Configure parameters (chỉ 1 lần ngay sau khi mở)
            logger.info("[4/5] Configuring camera parameters...")
            self._configure_camera()
            logger.info("Camera configured")
            
            # [5] Allocate frame buffer
            logger.info("[5/5] Allocating frame buffer...")
            self._allocate_frame_buffer()
            logger.info("Frame buffer allocated")
            
            self._is_connected = True
            logger.info("=" * 60)
            logger.info(f"✓✓Camera connected successfully: {self._device_info.GetFriendlyName()}")
            logger.info("=" * 60)
            return True
            
        except self.mvsdk.CameraException as e:
            logger.error(f"MindVision CameraException({e.error_code}): {e.message}")
            self._cleanup_on_error()
            return False
        except Exception as e:
            logger.error(f"Failed to connect camera: {e}", exc_info=True)
            self._cleanup_on_error()
            return False
    
    def _cleanup_on_error(self):
        """Cleanup khi có lỗi trong quá trình connect"""
        if self._handle is not None:
            try:
                self.mvsdk.CameraUnInit(self._handle)
            except:
                pass
            self._handle = None
        self._device_info = None
        self._cap = None
    
    def disconnect(self) -> bool:
        if not self._is_connected:
            return True
        
        try:
            logger.info(f"Disconnecting camera: {self.camera_id}")
            
            # 1. Stop grabbing nếu đang grab
            if self._is_grabbing:
                self.stop_grabbing()
            
            # 2. Free frame buffer
            if self._frame_buffer is not None:
                try:
                    self.mvsdk.CameraAlignFree(self._frame_buffer)
                    logger.info("Frame buffer freed")
                except:
                    pass
                self._frame_buffer = None
            
            # 3. Uninit camera (close device + destroy handle)
            if self._handle is not None:
                self.mvsdk.CameraUnInit(self._handle)
                self._handle = None
                logger.info("Camera uninitialized")
            
            self._is_connected = False
            self._device_info = None
            self._cap = None
            
            logger.info("Camera disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect camera: {e}", exc_info=True)
            return False
    
    def start_grabbing(self) -> bool:
        """
        [4] Start grab - Bắt đầu streaming
        SDK sẽ tự động lấy ảnh liên tục vào buffer
        """
        if not self._is_connected:
            logger.error("Cannot start grabbing: not connected")
            return False
        
        try:
            logger.info("[4] Starting grabbing (CameraPlay)...")
            self.mvsdk.CameraPlay(self._handle)
            self._is_grabbing = True
            logger.info("Grabbing started - camera is streaming")
            return True
        except self.mvsdk.CameraException as e:
            logger.error(f"CameraPlay failed({e.error_code}): {e.message}")
            return False
        except Exception as e:
            logger.error(f"Failed to start grabbing: {e}", exc_info=True)
            return False
    
    def stop_grabbing(self) -> bool:
        """Dừng grab - Pause camera"""
        if not self._is_grabbing:
            return True
        
        try:
            logger.info("Stopping grabbing (CameraPause)...")
            self.mvsdk.CameraPause(self._handle)
            self._is_grabbing = False
            logger.info("Grabbing stopped")
            return True
        except self.mvsdk.CameraException as e:
            logger.error(f"CameraPause failed({e.error_code}): {e.message}")
            return False
        except Exception as e:
            logger.error(f"Failed to stop grabbing: {e}", exc_info=True)
            return False
    
    def capture_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
        if not self._is_connected or not self._is_grabbing:
            logger.error("Cannot capture: camera not ready (connected={}, grabbing={})".format(
                self._is_connected, self._is_grabbing))
            return None
        
        pRawData = None
        try:
            # [5.1] Get raw frame buffer from camera
            pRawData, FrameHead = self.mvsdk.CameraGetImageBuffer(self._handle, timeout_ms)
            
            # [5.2] Process image: RAW → RGB/MONO (dùng buffer đã allocate sẵn)
            self.mvsdk.CameraImageProcess(self._handle, pRawData, self._frame_buffer, FrameHead)
            
            # [5.3] Convert buffer → NumPy array
            if self._mono_camera:
                # Grayscale (Mono8)
                frame_data = (self.mvsdk.c_ubyte * FrameHead.iWidth * FrameHead.iHeight).from_address(self._frame_buffer)
                image = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                    (FrameHead.iHeight, FrameHead.iWidth)
                )
            else:
                # RGB color
                frame_data = (self.mvsdk.c_ubyte * FrameHead.iWidth * FrameHead.iHeight * 3).from_address(self._frame_buffer)
                image = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                    (FrameHead.iHeight, FrameHead.iWidth, 3)
                )
            
            # ⚠️ IMPORTANT: Copy data trước khi release buffer
            # Nếu không copy, data sẽ corrupt khi buffer bị ghi đè
            image = image.copy()                                                                                                             
            return image
            
        except self.mvsdk.CameraException as e:
            if e.error_code == self.mvsdk.CAMERA_STATUS_TIME_OUT:
                # Timeout không phải lỗi nghiêm trọng, chỉ warning
                logger.warning(f"Frame timeout ({timeout_ms}ms)")
            else:
                logger.error(f"CameraGetImageBuffer failed({e.error_code}): {e.message}")
            return None
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}", exc_info=True)
            return None
            
        finally:
            # ⚠️⚠️⚠️ CRITICAL: Always release raw buffer!
            # Đảm bảo release ngay cả khi có exception
            if pRawData is not None:
                try:
                    self.mvsdk.CameraReleaseImageBuffer(self._handle, pRawData)
                except Exception as e:
                    logger.error(f"Failed to release buffer: {e}")
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """Set camera parameter (dùng trong runtime nếu cần)"""
        if not self._is_connected:
            return False
        
        try:
            if param_name == 'ExposureTime':
                self.mvsdk.CameraSetExposureTime(self._handle, value)
            elif param_name == 'Gain':
                self.mvsdk.CameraSetAnalogGain(self._handle, value)
            elif param_name == 'Gamma':
                # Gamma (Brightness) - range typically 1-100
                self.mvsdk.CameraSetGamma(self._handle, value)
            elif param_name == 'Contrast':
                # Contrast - range typically -100 to 100
                self.mvsdk.CameraSetContrast(self._handle, value)
            elif param_name == 'Saturation':
                # Saturation - range typically 0-100 (for color cameras)
                self.mvsdk.CameraSetSaturation(self._handle, value)
            elif param_name == 'ZoomWidth' or param_name == 'ZoomHeight':
                # Zoom requires setting resolution with zoom parameters
                # This is more complex, will handle separately
                logger.warning(f"Zoom parameter requires resolution change, use set_zoom() method")
                return False
            else:
                logger.warning(f"Unknown parameter: {param_name}")
                return False
            
            logger.info(f"Set {param_name} = {value}")
            return True
            
        except self.mvsdk.CameraException as e:
            logger.error(f"Set {param_name} failed({e.error_code}): {e.message}")
            return False
        except Exception as e:
            logger.error(f"Set {param_name} failed: {e}")
            return False
    
    def get_parameter(self, param_name: str) -> Optional[Any]:
        """Get camera parameter"""
        if not self._is_connected:
            return None
        
        try:
            if param_name == 'ExposureTime':
                return self.mvsdk.CameraGetExposureTime(self._handle)
            elif param_name == 'Gain':
                return self.mvsdk.CameraGetAnalogGain(self._handle)
            elif param_name == 'Gamma':
                return self.mvsdk.CameraGetGamma(self._handle)
            elif param_name == 'Contrast':
                return self.mvsdk.CameraGetContrast(self._handle)
            elif param_name == 'Saturation':
                return self.mvsdk.CameraGetSaturation(self._handle)
            else:
                return None
        except Exception as e:
            logger.error(f"Get {param_name} failed: {e}")
            return None
    
    def _enumerate_devices(self) -> List:
        try:
            device_list = self.mvsdk.CameraEnumerateDevice()
            nDev = len(device_list)
            
            if nDev < 1:
                logger.warning("No camera found")
                return []
            
            # Log tất cả cameras tìm được
            logger.info(f"Found {nDev} camera(s):")
            for i, dev in enumerate(device_list):
                logger.info(f"  [{i}] {dev.GetFriendlyName()} - {dev.GetPortType()} (SN: {dev.GetSn()})")
            
            return device_list
            
        except self.mvsdk.CameraException as e:
            logger.error(f"CameraEnumerateDevice failed({e.error_code}): {e.message}")
            return []
        except Exception as e:
            logger.error(f"Failed to enumerate devices: {e}", exc_info=True)
            return []
    
    def _select_camera(self, device_list: List):
        """
        [2.1] Select camera - Chọn camera theo camera_id
        
        camera_id có thể là:
        - "cam2", "cam1", "cam0" → chọn camera theo index
        - "auto" → chọn camera đầu tiên
        - số index: "0", "1", "2" → chọn theo index
        - serial number → chọn theo SN
        
        Returns: tSdkCameraDevInfo hoặc None
        """
        try:
            nDev = len(device_list)
            
            if nDev < 1:
                return None
            
            # Parse camera_id
            camera_index = None
            
            if self.camera_id.lower() == "auto":
                camera_index = 0
                logger.info("Auto mode: selecting first camera")
                
            elif self.camera_id.lower().startswith("cam"):
                # "cam0", "cam1", "cam2" → extract index
                try:
                    camera_index = int(self.camera_id[3:])
                    logger.info(f"Cam mode: selecting camera index {camera_index}")
                except:
                    logger.error(f"Invalid camera_id format: {self.camera_id}")
                    return None
                    
            elif self.camera_id.isdigit():
                # "0", "1", "2" → direct index
                camera_index = int(self.camera_id)
                logger.info(f"Index mode: selecting camera {camera_index}")
                
            else:
                # Assume it's serial number
                logger.info(f"SN mode: searching for camera with SN: {self.camera_id}")
                for dev in device_list:
                    if dev.GetSn() == self.camera_id:
                        logger.info(f"Found camera by SN: {dev.GetFriendlyName()}")
                        return dev
                logger.error(f"Camera with SN '{self.camera_id}' not found")
                return None
            
            # Check index validity
            if camera_index is not None:
                if 0 <= camera_index < nDev:
                    selected = device_list[camera_index]
                    logger.info(f"Selected camera [{camera_index}]: {selected.GetFriendlyName()}")
                    return selected
                else:
                    logger.error(f"Camera index {camera_index} out of range (available: 0-{nDev-1})")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting camera: {e}", exc_info=True)
            return None
    
    def _allocate_frame_buffer(self):
        """
        [5] Allocate frame buffer - Cấp phát bộ nhớ cho frame
        Buffer này dùng để chứa ảnh đã xử lý (RGB/MONO)
        """
        try:
            # Tính kích thước buffer cần thiết
            width_max = self._cap.sResolutionRange.iWidthMax
            height_max = self._cap.sResolutionRange.iHeightMax
            
            # Mono camera = 1 byte/pixel, Color = 3 bytes/pixel
            bytes_per_pixel = 1 if self._mono_camera else 3
            buffer_size = width_max * height_max * bytes_per_pixel
            
            # Allocate aligned memory (16-byte alignment)
            self._frame_buffer = self.mvsdk.CameraAlignMalloc(buffer_size, 16)
            
            logger.info(f"Buffer allocated: {width_max}x{height_max}x{bytes_per_pixel} = {buffer_size} bytes")
            
        except Exception as e:
            logger.error(f"Failed to allocate frame buffer: {e}")
            raise
    
    def _configure_camera(self):
        try:
            # Lấy config từ YAML
            exposure_time = self.config.get('exposure_time', 30000)  # 30ms default
            gain = self.config.get('gain', 0)
            trigger_mode = self.config.get('trigger_mode', 'off')
            pixel_format = self.config.get('pixel_format', 'auto').lower()  # auto, mono8, rgb8
            
            # Set output format based on pixel_format config
            if pixel_format == 'mono8':
                # Force MONO8 output
                self.mvsdk.CameraSetIspOutFormat(self._handle, self.mvsdk.CAMERA_MEDIA_TYPE_MONO8)
                self._mono_camera = True  # Override detection
                logger.info("  Output format: MONO8 (forced by config)")
            elif pixel_format == 'rgb8':
                # Force RGB8 output
                if self._mono_camera:
                    # Convert mono to RGB
                    logger.info("  Output format: RGB8 (mono sensor expanded to RGB)")
                else:
                    logger.info("  Output format: RGB8")
                self._mono_camera = False  # Override detection
            else:
                # Auto mode - use sensor type
                if self._mono_camera:
                    # Mono camera → output MONO8 (không mở rộng thành RGB)
                    self.mvsdk.CameraSetIspOutFormat(self._handle, self.mvsdk.CAMERA_MEDIA_TYPE_MONO8)
                    logger.info("  Output format: MONO8 (auto)")
                else:
                    # Color camera → output RGB
                    logger.info("  Output format: RGB8 (auto)")
            
            trig_mode = 0 if trigger_mode.lower() == 'off' else 1
            self.mvsdk.CameraSetTriggerMode(self._handle, trig_mode)
            logger.info(f"  Trigger mode: {'Continuous' if trig_mode == 0 else 'Software trigger'}")
            
            # [4.3] Set manual exposure (theo spec: ExposureAuto OFF)
            self.mvsdk.CameraSetAeState(self._handle, 0)  # 0=manual, 1=auto
            self.mvsdk.CameraSetExposureTime(self._handle, exposure_time)
            logger.info(f"  Exposure: Manual, {exposure_time} μs ({exposure_time/1000.0:.1f} ms)")
            
            # [4.4] Set gain (optional)
            if gain > 0:
                try:
                    self.mvsdk.CameraSetAnalogGain(self._handle, gain)
                    logger.info(f"  Gain: {gain}")
                except:
                    pass
            
            logger.info("Camera parameters configured")
            
        except self.mvsdk.CameraException as e:
            logger.error(f"Config failed({e.error_code}): {e.message}")
            raise
        except Exception as e:
            logger.error(f"Error configuring camera: {e}", exc_info=True)
            raise
    
    def get_info(self) -> Dict[str, Any]:
        """Lấy thông tin camera chi tiết"""
        info = super().get_info()
        
        # Thông tin cơ bản
        info.update({
            'type': 'MindVision',
            'sdk_available': self.mvsdk is not None,
            'handle': self._handle,
        })
        
        # Thông tin device (nếu đã kết nối)
        if self._device_info is not None:
            info.update({
                'friendly_name': self._device_info.GetFriendlyName(),
                'serial_number': self._device_info.GetSn(),
                'port_type': self._device_info.GetPortType(),
                'sensor_type': self._device_info.GetSensorType(),
            })
        
        # Thông tin capability (nếu có)
        if self._cap is not None:
            info.update({
                'resolution_max': f"{self._cap.sResolutionRange.iWidthMax}x{self._cap.sResolutionRange.iHeightMax}",
                'mono_camera': self._mono_camera,
            })
        
        return info

