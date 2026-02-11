"""
MVS Camera (Hikvision) Implementation
Dựa trên MVS SDK Python - theo tutorial và BasicDemo
"""
import numpy as np
from typing import Optional, Dict, Any, List
from .camera_base import CameraBase
import logging
from ctypes import *
import sys
import os

logger = logging.getLogger(__name__)


class MVSCamera(CameraBase):
    """
    Camera implementation cho MVS SDK (Hikvision)
    Flow kết nối:
    [1] Initialize SDK → [2] Enumerate → [3] Create Handle → [4] Open Device 
    → [5] Config Packet Size (GigE) → [6] Set Parameters → [7] Start Grabbing
    """
    
    def __init__(self, camera_id: str, config: Dict[str, Any]):
        super().__init__(camera_id, config)
        self._cam = None
        self._device_list = None
        self._device_index = None
        self._is_gige = False
        self._stDeviceList = None
        
        # Import MVS SDK
        try:
            # Add MvImport to path
            mvs_import_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'MvImport')
            if os.path.exists(mvs_import_path) and mvs_import_path not in sys.path:
                sys.path.insert(0, mvs_import_path)
            
            # Add DLL path to os.environ for ctypes to find MvCameraControl.dll
            # Try multiple locations: project root, MVS installation
            project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
            project_root = os.path.abspath(project_root)
            
            dll_search_paths = [
                project_root,  # Project root (where MvCameraControl.dll is)
                r"C:\Program Files\MVS\Runtime\Win64_x64",
                r"C:\Program Files\MVS\Runtime\Win64",
                r"C:\Program Files (x86)\MVS\Runtime\Win64_x64",
                r"C:\Program Files (x86)\MVS\Runtime\Win64",
            ]
            
            # Add all existing paths to PATH
            for dll_path in dll_search_paths:
                if os.path.exists(dll_path):
                    current_path = os.environ.get('PATH', '')
                    if dll_path not in current_path:
                        os.environ['PATH'] = dll_path + os.pathsep + current_path
                        logger.info(f"Added DLL path: {dll_path}")
            
            from MvCameraControl_class import MvCamera, MV_CC_DEVICE_INFO_LIST, \
                MV_GIGE_DEVICE, MV_USB_DEVICE, MV_CC_DEVICE_INFO, \
                MV_FRAME_OUT, MV_FRAME_OUT_INFO_EX, MV_ACCESS_Exclusive, \
                MV_TRIGGER_MODE_OFF, MV_TRIGGER_MODE_ON, MV_TRIGGER_SOURCE_SOFTWARE
            from MvErrorDefine_const import MV_OK, MV_E_HANDLE
            # MV_E_TIMEOUT doesn't exist, use MV_E_GC_TIMEOUT or define it
            try:
                from MvErrorDefine_const import MV_E_TIMEOUT
            except ImportError:
                # Fallback: use GC_TIMEOUT or define a custom timeout constant
                try:
                    from MvErrorDefine_const import MV_E_GC_TIMEOUT as MV_E_TIMEOUT
                except ImportError:
                    MV_E_TIMEOUT = 0x800700 # Custom timeout error code
            from PixelType_header import PixelType_Gvsp_Mono8, PixelType_Gvsp_RGB8_Packed, \
                PixelType_Gvsp_BayerGR8, PixelType_Gvsp_BayerRG8, \
                PixelType_Gvsp_BayerGB8, PixelType_Gvsp_BayerBG8
            
            self.MvCamera = MvCamera
            self.MV_CC_DEVICE_INFO_LIST = MV_CC_DEVICE_INFO_LIST
            self.MV_GIGE_DEVICE = MV_GIGE_DEVICE
            self.MV_USB_DEVICE = MV_USB_DEVICE
            self.MV_CC_DEVICE_INFO = MV_CC_DEVICE_INFO
            self.MV_FRAME_OUT = MV_FRAME_OUT
            self.MV_FRAME_OUT_INFO_EX = MV_FRAME_OUT_INFO_EX
            self.MV_ACCESS_Exclusive = MV_ACCESS_Exclusive
            self.MV_TRIGGER_MODE_OFF = MV_TRIGGER_MODE_OFF
            self.MV_TRIGGER_MODE_ON = MV_TRIGGER_MODE_ON
            self.MV_TRIGGER_SOURCE_SOFTWARE = MV_TRIGGER_SOURCE_SOFTWARE
            self.MV_OK = MV_OK
            self.MV_E_HANDLE = MV_E_HANDLE
            self.MV_E_TIMEOUT = MV_E_TIMEOUT
            self.PixelType_Gvsp_Mono8 = PixelType_Gvsp_Mono8
            self.PixelType_Gvsp_RGB8_Packed = PixelType_Gvsp_RGB8_Packed
            
            # Bayer patterns
            self.bayer_patterns = [
                PixelType_Gvsp_BayerGR8, PixelType_Gvsp_BayerRG8,
                PixelType_Gvsp_BayerGB8, PixelType_Gvsp_BayerBG8
            ]
            
            logger.info("✓ MVS SDK loaded successfully from MvImport")
            
        except ImportError as e:
            logger.error(f"Cannot import MVS SDK: {e}")
            logger.error("Make sure MvImport folder exists with all required files")
            raise
    
    def connect(self) -> bool:
        """
        Kết nối camera theo MVS SDK flow
        """
        try:
            logger.info("=" * 60)
            logger.info(f"[MVS] Connecting to camera: {self.camera_id}")
            
            # [1] Initialize SDK (chỉ cần gọi 1 lần khi app start)
            # Thường gọi trong main.py, nhưng để an toàn ta gọi ở đây
            logger.info("[1/7] Initializing MVS SDK...")
            ret = self.MvCamera.MV_CC_Initialize()
            if ret != self.MV_OK:
                logger.warning(f"SDK already initialized or init failed: {self._to_hex_str(ret)}")
            
            # [2] Enumerate devices - tìm tất cả camera
            logger.info("[2/7] Enumerating devices...")
            self._device_list = self.MV_CC_DEVICE_INFO_LIST()
            tlayer_type = self.MV_GIGE_DEVICE | self.MV_USB_DEVICE
            ret = self.MvCamera.MV_CC_EnumDevices(tlayer_type, self._device_list)
            
            if ret != self.MV_OK:
                logger.error(f"Enum devices failed: {self._to_hex_str(ret)}")
                return False
            
            if self._device_list.nDeviceNum == 0:
                logger.error("No MVS camera found")
                return False
            
            logger.info(f"Found {self._device_list.nDeviceNum} camera(s)")
            
            # [2.1] Select camera
            logger.info("[2.1] Selecting camera...")
            self._device_index = self._select_camera()
            if self._device_index is None:
                logger.error(f"Cannot select camera: {self.camera_id}")
                return False
            
            # Get device info
            self._stDeviceList = cast(
                self._device_list.pDeviceInfo[self._device_index],
                POINTER(self.MV_CC_DEVICE_INFO)
            ).contents
            
            # Check if GigE device
            self._is_gige = (self._stDeviceList.nTLayerType == self.MV_GIGE_DEVICE)
            
            logger.info(f"Selected camera [{self._device_index}]: {self._get_device_name()}")
            
            # [3] Create Handle
            logger.info("[3/7] Creating camera handle...")
            self._cam = self.MvCamera()
            ret = self._cam.MV_CC_CreateHandle(self._stDeviceList)
            if ret != self.MV_OK:
                logger.error(f"Create handle failed: {self._to_hex_str(ret)}")
                self._cam = None
                return False
            
            logger.info("Camera handle created")
            
            # [4] Open Device
            logger.info("[4/7] Opening device...")
            ret = self._cam.MV_CC_OpenDevice(self.MV_ACCESS_Exclusive, 0)
            if ret != self.MV_OK:
                logger.error(f"Open device failed: {self._to_hex_str(ret)}")
                self._cleanup_on_error()
                return False
            
            logger.info("Device opened")
            
            # [5] Optimize Packet Size for GigE
            if self._is_gige:
                logger.info("[5/7] Optimizing packet size for GigE...")
                packet_size = self._cam.MV_CC_GetOptimalPacketSize()
                if int(packet_size) > 0:
                    ret = self._cam.MV_CC_SetIntValue("GevSCPSPacketSize", packet_size)
                    if ret == self.MV_OK:
                        logger.info(f"Packet size set to {packet_size}")
                    else:
                        logger.warning(f"Set packet size failed: {self._to_hex_str(ret)}")
                else:
                    logger.warning("Cannot get optimal packet size")
            else:
                logger.info("[5/7] Not GigE, skipping packet size optimization")
            
            # [6] Configure camera parameters
            logger.info("[6/7] Configuring camera parameters...")
            self._configure_camera()
            logger.info("Camera configured")
            
            self._is_connected = True
            logger.info("=" * 60)
            logger.info(f"✓✓ MVS Camera connected successfully: {self._get_device_name()}")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect MVS camera: {e}", exc_info=True)
            self._cleanup_on_error()
            return False
    
    def disconnect(self) -> bool:
        if not self._is_connected:
            return True
        
        try:
            logger.info(f"Disconnecting MVS camera: {self.camera_id}")
            
            # 1. Stop grabbing nếu đang grab
            if self._is_grabbing:
                self.stop_grabbing()
            
            # 2. Close device
            if self._cam is not None:
                ret = self._cam.MV_CC_CloseDevice()
                if ret != self.MV_OK:
                    logger.warning(f"Close device warning: {self._to_hex_str(ret)}")
                
                # 3. Destroy handle
                ret = self._cam.MV_CC_DestroyHandle()
                if ret != self.MV_OK:
                    logger.warning(f"Destroy handle warning: {self._to_hex_str(ret)}")
                
                self._cam = None
                logger.info("Camera closed and handle destroyed")
            
            self._is_connected = False
            self._device_list = None
            self._device_index = None
            self._stDeviceList = None
            
            logger.info("MVS Camera disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect MVS camera: {e}", exc_info=True)
            return False
    
    def start_grabbing(self) -> bool:
        """[7] Start grabbing - bắt đầu streaming"""
        if not self._is_connected:
            logger.error("Cannot start grabbing: not connected")
            return False
        
        try:
            logger.info("[7] Starting grabbing...")
            ret = self._cam.MV_CC_StartGrabbing()
            if ret != self.MV_OK:
                logger.error(f"Start grabbing failed: {self._to_hex_str(ret)}")
                return False
            
            self._is_grabbing = True
            logger.info("Grabbing started - camera is streaming")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start grabbing: {e}", exc_info=True)
            return False
    
    def stop_grabbing(self) -> bool:
        """Stop grabbing"""
        if not self._is_grabbing:
            return True
        
        try:
            logger.info("Stopping grabbing...")
            ret = self._cam.MV_CC_StopGrabbing()
            if ret != self.MV_OK:
                logger.error(f"Stop grabbing failed: {self._to_hex_str(ret)}")
                return False
            
            self._is_grabbing = False
            logger.info("Grabbing stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop grabbing: {e}", exc_info=True)
            return False
    
    def capture_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
        """
        Capture frame using MV_CC_GetImageBuffer
        Theo tutorial và BasicDemo
        """
        if not self._is_connected or not self._is_grabbing:
            logger.error("Cannot capture: camera not ready (connected={}, grabbing={})".format(
                self._is_connected, self._is_grabbing))
            return None
        
        stOutFrame = self.MV_FRAME_OUT()
        memset(byref(stOutFrame), 0, sizeof(stOutFrame))
        
        try:
            # Get image buffer
            ret = self._cam.MV_CC_GetImageBuffer(stOutFrame, timeout_ms)
            if ret != self.MV_OK:
                if ret == self.MV_E_TIMEOUT:
                    logger.debug(f"Frame timeout ({timeout_ms}ms)")
                else:
                    logger.warning(f"Get image buffer failed: {self._to_hex_str(ret)}")
                return None
            
            # Extract frame info
            frame_info = stOutFrame.stFrameInfo
            width = frame_info.nWidth
            height = frame_info.nHeight
            pixel_type = frame_info.enPixelType
            
            # Convert buffer to numpy array
            pData = cast(
                stOutFrame.pBufAddr,
                POINTER(c_ubyte * frame_info.nFrameLen)
            ).contents
            
            img_buffer = np.frombuffer(pData, dtype=np.uint8)
            
            # Process based on pixel format
            if pixel_type == self.PixelType_Gvsp_Mono8:
                # Grayscale
                image = img_buffer.reshape((height, width))
            elif pixel_type == self.PixelType_Gvsp_RGB8_Packed:
                # RGB
                image = img_buffer.reshape((height, width, 3))
            elif pixel_type in self.bayer_patterns:
                # Bayer pattern - convert to RGB using OpenCV
                try:
                    import cv2
                    img_bayer = img_buffer.reshape((height, width))
                    # Auto detect Bayer pattern and convert
                    image = cv2.cvtColor(img_bayer, cv2.COLOR_BAYER_RG2BGR)
                except Exception as e:
                    logger.warning(f"Bayer conversion failed: {e}, returning raw")
                    image = img_buffer.reshape((height, width))
            else:
                # Unknown format, try as mono
                logger.warning(f"Unknown pixel type: {pixel_type}, treating as mono")
                image = img_buffer.reshape((height, width))
            
            # IMPORTANT: Copy data before releasing buffer
            image = image.copy()
            
            return image
            
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}", exc_info=True)
            return None
        
        finally:
            # CRITICAL: Always release buffer
            if stOutFrame.pBufAddr is not None:
                try:
                    self._cam.MV_CC_FreeImageBuffer(stOutFrame)
                except Exception as e:
                    logger.error(f"Failed to free image buffer: {e}")
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """Set camera parameter"""
        if not self._is_connected:
            return False
        
        try:
            if param_name == 'ExposureTime':
                # Set manual exposure first
                self._cam.MV_CC_SetEnumValue("ExposureAuto", 0)
                ret = self._cam.MV_CC_SetFloatValue("ExposureTime", float(value))
            elif param_name == 'Gain':
                ret = self._cam.MV_CC_SetFloatValue("Gain", float(value))
            elif param_name == 'Gamma':
                ret = self._cam.MV_CC_SetFloatValue("Gamma", float(value))
            elif param_name == 'FrameRate':
                ret = self._cam.MV_CC_SetFloatValue("AcquisitionFrameRate", float(value))
            else:
                logger.warning(f"Unknown parameter: {param_name}")
                return False
            
            if ret == self.MV_OK:
                logger.info(f"Set {param_name} = {value}")
                return True
            else:
                logger.error(f"Set {param_name} failed: {self._to_hex_str(ret)}")
                return False
                
        except Exception as e:
            logger.error(f"Set {param_name} failed: {e}")
            return False
    
    def get_parameter(self, param_name: str) -> Optional[Any]:
        """Get camera parameter"""
        if not self._is_connected:
            return None
        
        try:
            from CameraParams_header import MVCC_FLOATVALUE
            
            stFloatValue = MVCC_FLOATVALUE()
            memset(byref(stFloatValue), 0, sizeof(MVCC_FLOATVALUE))
            
            if param_name == 'ExposureTime':
                ret = self._cam.MV_CC_GetFloatValue("ExposureTime", stFloatValue)
            elif param_name == 'Gain':
                ret = self._cam.MV_CC_GetFloatValue("Gain", stFloatValue)
            elif param_name == 'Gamma':
                ret = self._cam.MV_CC_GetFloatValue("Gamma", stFloatValue)
            elif param_name == 'FrameRate':
                ret = self._cam.MV_CC_GetFloatValue("AcquisitionFrameRate", stFloatValue)
            else:
                return None
            
            if ret == self.MV_OK:
                return stFloatValue.fCurValue
            else:
                logger.error(f"Get {param_name} failed: {self._to_hex_str(ret)}")
                return None
                
        except Exception as e:
            logger.error(f"Get {param_name} failed: {e}")
            return None
    
    def get_parameter_range(self, param_name: str) -> Optional[tuple]:
        """Get parameter range"""
        if not self._is_connected:
            return None
        
        try:
            from CameraParams_header import MVCC_FLOATVALUE
            
            stFloatValue = MVCC_FLOATVALUE()
            memset(byref(stFloatValue), 0, sizeof(MVCC_FLOATVALUE))
            
            if param_name == 'ExposureTime':
                ret = self._cam.MV_CC_GetFloatValue("ExposureTime", stFloatValue)
            elif param_name == 'Gain':
                ret = self._cam.MV_CC_GetFloatValue("Gain", stFloatValue)
            elif param_name == 'Gamma':
                ret = self._cam.MV_CC_GetFloatValue("Gamma", stFloatValue)
            elif param_name == 'FrameRate':
                ret = self._cam.MV_CC_GetFloatValue("AcquisitionFrameRate", stFloatValue)
            else:
                return None
            
            if ret == self.MV_OK:
                return (stFloatValue.fMin, stFloatValue.fMax)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Get range {param_name} failed: {e}")
            return None
    
    def _configure_camera(self):
        """Configure camera parameters from config"""
        try:
            # Get config
            exposure_time = self.config.get('exposure_time', 30000)  # 30ms default
            gain = self.config.get('gain', 0)
            trigger_mode = self.config.get('trigger_mode', 'off')
            
            # [6.1] Set trigger mode
            if trigger_mode.lower() == 'off':
                ret = self._cam.MV_CC_SetEnumValue("TriggerMode", self.MV_TRIGGER_MODE_OFF)
                logger.info("  Trigger mode: Continuous (OFF)")
            else:
                ret = self._cam.MV_CC_SetEnumValue("TriggerMode", self.MV_TRIGGER_MODE_ON)
                ret = self._cam.MV_CC_SetEnumValue("TriggerSource", self.MV_TRIGGER_SOURCE_SOFTWARE)
                logger.info("  Trigger mode: Software trigger")
            
            if ret != self.MV_OK:
                logger.warning(f"Set trigger mode failed: {self._to_hex_str(ret)}")
            
            # [6.2] Set exposure (manual)
            ret = self._cam.MV_CC_SetEnumValue("ExposureAuto", 0)  # Manual
            if ret == self.MV_OK:
                ret = self._cam.MV_CC_SetFloatValue("ExposureTime", float(exposure_time))
                if ret == self.MV_OK:
                    logger.info(f"  Exposure: Manual, {exposure_time} μs ({exposure_time/1000.0:.1f} ms)")
                else:
                    logger.warning(f"Set exposure failed: {self._to_hex_str(ret)}")
            
            # [6.3] Set gain
            if gain > 0:
                ret = self._cam.MV_CC_SetFloatValue("Gain", float(gain))
                if ret == self.MV_OK:
                    logger.info(f"  Gain: {gain}")
                else:
                    logger.warning(f"Set gain failed: {self._to_hex_str(ret)}")
            
            logger.info("Camera parameters configured")
            
        except Exception as e:
            logger.error(f"Error configuring camera: {e}", exc_info=True)
            raise
    
    def _select_camera(self) -> Optional[int]:
        """
        Select camera based on camera_id
        Returns: device index or None
        """
        try:
            num_devices = self._device_list.nDeviceNum
            
            # Log all available cameras
            logger.info(f"Available cameras:")
            for i in range(num_devices):
                dev_info = cast(
                    self._device_list.pDeviceInfo[i],
                    POINTER(self.MV_CC_DEVICE_INFO)
                ).contents
                name = self._get_device_name_from_info(dev_info)
                logger.info(f"  [{i}] {name}")
            
            # Parse camera_id
            if self.camera_id.lower() == "auto":
                logger.info("Auto mode: selecting first camera")
                return 0
            
            elif self.camera_id.lower().startswith("cam"):
                # "cam0", "cam1", "cam2"
                try:
                    index = int(self.camera_id[3:])
                    if 0 <= index < num_devices:
                        logger.info(f"Cam mode: selecting camera index {index}")
                        return index
                    else:
                        logger.error(f"Camera index {index} out of range (available: 0-{num_devices-1})")
                        return None
                except:
                    logger.error(f"Invalid camera_id format: {self.camera_id}")
                    return None
            
            elif self.camera_id.isdigit():
                # "0", "1", "2"
                index = int(self.camera_id)
                if 0 <= index < num_devices:
                    logger.info(f"Index mode: selecting camera {index}")
                    return index
                else:
                    logger.error(f"Camera index {index} out of range (available: 0-{num_devices-1})")
                    return None
            
            else:
                # Assume serial number or name
                logger.info(f"Searching for camera by name/SN: {self.camera_id}")
                for i in range(num_devices):
                    dev_info = cast(
                        self._device_list.pDeviceInfo[i],
                        POINTER(self.MV_CC_DEVICE_INFO)
                    ).contents
                    name = self._get_device_name_from_info(dev_info)
                    if self.camera_id in name:
                        logger.info(f"Found camera by name: {name}")
                        return i
                
                logger.error(f"Camera '{self.camera_id}' not found")
                return None
            
        except Exception as e:
            logger.error(f"Error selecting camera: {e}", exc_info=True)
            return None
    
    def _get_device_name(self) -> str:
        """Get device name from current selected device"""
        if self._stDeviceList is None:
            return "Unknown"
        return self._get_device_name_from_info(self._stDeviceList)
    
    def _get_device_name_from_info(self, dev_info) -> str:
        """Get device name from device info structure"""
        try:
            if dev_info.nTLayerType == self.MV_GIGE_DEVICE:
                # GigE device
                model_name = self._decode_char(dev_info.SpecialInfo.stGigEInfo.chModelName)
                user_name = self._decode_char(dev_info.SpecialInfo.stGigEInfo.chUserDefinedName)
                nip1 = ((dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
                nip2 = ((dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
                nip3 = ((dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
                nip4 = (dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
                ip = f"{nip1}.{nip2}.{nip3}.{nip4}"
                return f"GigE: {user_name} {model_name} ({ip})"
            
            elif dev_info.nTLayerType == self.MV_USB_DEVICE:
                # USB device
                model_name = self._decode_char(dev_info.SpecialInfo.stUsb3VInfo.chModelName)
                user_name = self._decode_char(dev_info.SpecialInfo.stUsb3VInfo.chUserDefinedName)
                sn = self._decode_char(dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber)
                return f"USB: {user_name} {model_name} ({sn})"
            
            else:
                return "Unknown device type"
                
        except Exception as e:
            logger.warning(f"Error getting device name: {e}")
            return "Unknown"
    
    def _decode_char(self, ctypes_char_array) -> str:
        """Decode ctypes char array to string (from BasicDemo)"""
        try:
            byte_str = memoryview(ctypes_char_array).tobytes()
            
            # Truncate at null byte
            null_index = byte_str.find(b'\x00')
            if null_index != -1:
                byte_str = byte_str[:null_index]
            
            # Try multiple encodings
            for encoding in ['gbk', 'utf-8', 'latin-1']:
                try:
                    return byte_str.decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            # Fallback
            return byte_str.decode('latin-1', errors='replace')
        except:
            return ""
    
    def _to_hex_str(self, num) -> str:
        """Convert error code to hex string"""
        chaDic = {10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f'}
        hexStr = ""
        if num < 0:
            num = num + 2 ** 32
        while num >= 16:
            digit = num % 16
            hexStr = chaDic.get(digit, str(digit)) + hexStr
            num //= 16
        hexStr = chaDic.get(num, str(num)) + hexStr
        return "0x" + hexStr
    
    def _cleanup_on_error(self):
        """Cleanup on connection error"""
        if self._cam is not None:
            try:
                self._cam.MV_CC_DestroyHandle()
            except:
                pass
            self._cam = None
        self._device_list = None
        self._device_index = None
        self._stDeviceList = None
    
    def get_info(self) -> Dict[str, Any]:
        """Get camera info"""
        info = super().get_info()
        
        info.update({
            'type': 'MVS',
            'sdk': 'Hikvision MVS',
        })
        
        if self._stDeviceList is not None:
            info.update({
                'device_name': self._get_device_name(),
                'device_type': 'GigE' if self._is_gige else 'USB',
            })
        
        return info
