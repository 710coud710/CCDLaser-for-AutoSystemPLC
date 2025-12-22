# MindVision SDK Integration Guide

Hướng dẫn tích hợp MindVision SDK vào CCDLaser.

## 1. Tổng quan

File `app/model/camera/mindvision_camera.py` đã được chuẩn bị sẵn với placeholder code. Bạn chỉ cần:

1. Cài đặt MindVision SDK
2. Import SDK vào code
3. Uncomment và điều chỉnh các SDK calls
4. Test với camera thật

## 2. Cài đặt MindVision SDK

### 2.1 Download SDK

1. Truy cập: http://www.mindvision.com.cn/
2. Tìm mục "Download" hoặc "下载中心"
3. Download:
   - **MindVision SDK** (Windows version)
   - **Python Wrapper** (nếu có riêng)

### 2.2 Cài đặt SDK

```bash
# Run installer
MindVision_SDK_Setup.exe

# Thường cài vào:
C:\Program Files\MindVision\
```

### 2.3 Cài đặt Python Wrapper

```bash
# Nếu có file .whl
pip install mvsdk-x.x.x-py3-none-any.whl

# Hoặc nếu có setup.py
cd path\to\python_wrapper
python setup.py install
```

### 2.4 Verify Installation

```python
import mvsdk
print(mvsdk.__version__)
```

## 3. SDK API Reference

### 3.1 Enumerate Devices

```python
import mvsdk

# Enumerate all cameras
device_list = mvsdk.CameraEnumerateDevice()

# device_list is array of tSdkCameraDevInfo
for device in device_list:
    print(f"Camera: {device.acFriendlyName}")
    print(f"  SN: {device.acSn}")
    print(f"  IP: {device.IpAddress}")
```

### 3.2 Initialize Camera

```python
# Create handle
hCamera = mvsdk.CameraInit(device_info, -1, -1)

# Get capability
cap = mvsdk.CameraGetCapability(hCamera)

# Play (start grabbing)
mvsdk.CameraPlay(hCamera)
```

### 3.3 Set Parameters

```python
# Set exposure time (microseconds)
mvsdk.CameraSetExposureTime(hCamera, 10000)

# Set gain (dB)
mvsdk.CameraSetAnalogGain(hCamera, 0)

# Set trigger mode
mvsdk.CameraSetTriggerMode(hCamera, 0)  # 0=off, 1=on

# Set pixel format
mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
```

### 3.4 Grab Frame

```python
# Get frame
pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 1000)  # 1000ms timeout

# Convert to RGB (if needed)
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameHead.iWidth * FrameHead.iHeight * 3, 16)
mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)

# Convert to NumPy array
import numpy as np
frame_data = (mvsdk.c_ubyte * FrameHead.iWidth * FrameHead.iHeight * 3).from_address(pFrameBuffer)
frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((FrameHead.iHeight, FrameHead.iWidth, 3))

# IMPORTANT: Release buffer
mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
mvsdk.CameraAlignFree(pFrameBuffer)
```

### 3.5 Cleanup

```python
# Stop grabbing
mvsdk.CameraPause(hCamera)

# Uninit camera
mvsdk.CameraUnInit(hCamera)
```

## 4. Integration Steps

### Step 1: Import SDK

Trong `mindvision_camera.py`, tìm dòng:

```python
try:
    # TODO: Import MindVision SDK khi có
    # import mvsdk
    # self.mvsdk = mvsdk
    logger.warning("MindVision SDK not imported - using placeholder")
    self.mvsdk = None
except ImportError as e:
    logger.error(f"Cannot import MindVision SDK: {e}")
    self.mvsdk = None
```

Thay bằng:

```python
try:
    import mvsdk
    self.mvsdk = mvsdk
    logger.info("MindVision SDK imported successfully")
except ImportError as e:
    logger.error(f"Cannot import MindVision SDK: {e}")
    self.mvsdk = None
```

### Step 2: Implement _enumerate_devices()

```python
def _enumerate_devices(self):
    """Quét tất cả camera MindVision trong mạng"""
    try:
        device_list = self.mvsdk.CameraEnumerateDevice()
        logger.info(f"Found {len(device_list)} camera(s)")
        return device_list
    except Exception as e:
        logger.error(f"Failed to enumerate devices: {e}")
        return []
```

### Step 3: Implement _find_camera_by_ip()

```python
def _find_camera_by_ip(self, device_list, ip_address: str):
    """Tìm camera theo IP"""
    for device in device_list:
        # Convert IP bytes to string
        device_ip = f"{device.IpAddress[0]}.{device.IpAddress[1]}.{device.IpAddress[2]}.{device.IpAddress[3]}"
        if device_ip == ip_address:
            logger.info(f"Found camera at {ip_address}")
            return device
    
    logger.warning(f"Camera {ip_address} not found")
    return None
```

### Step 4: Implement connect()

```python
def connect(self) -> bool:
    """Kết nối camera"""
    if self.mvsdk is None:
        logger.error("MindVision SDK not available")
        return False
    
    try:
        logger.info(f"Connecting to MindVision camera: {self.camera_id}")
        
        # 1. Enumerate devices
        device_list = self._enumerate_devices()
        if not device_list:
            logger.error("No MindVision camera found")
            return False
        
        # 2. Find camera by IP
        self._device_info = self._find_camera_by_ip(device_list, self.camera_id)
        if self._device_info is None:
            logger.error(f"Camera {self.camera_id} not found")
            return False
        
        # 3. Create handle
        self._handle = self.mvsdk.CameraInit(self._device_info, -1, -1)
        logger.info(f"Camera handle created: {self._handle}")
        
        # 4. Get capability
        self._cap = self.mvsdk.CameraGetCapability(self._handle)
        
        # 5. Set parameters
        self._configure_camera()
        
        self._is_connected = True
        logger.info(f"MindVision camera connected: {self.camera_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect camera: {e}", exc_info=True)
        return False
```

### Step 5: Implement disconnect()

```python
def disconnect(self) -> bool:
    """Ngắt kết nối"""
    if not self._is_connected:
        return True
    
    try:
        logger.info(f"Disconnecting camera: {self.camera_id}")
        
        # 1. Stop grabbing
        if self._is_grabbing:
            self.stop_grabbing()
        
        # 2. Uninit camera
        if self._handle is not None:
            self.mvsdk.CameraUnInit(self._handle)
            self._handle = None
        
        self._is_connected = False
        logger.info("Camera disconnected")
        return True
        
    except Exception as e:
        logger.error(f"Failed to disconnect camera: {e}", exc_info=True)
        return False
```

### Step 6: Implement start_grabbing()

```python
def start_grabbing(self) -> bool:
    """Bắt đầu grab"""
    if not self._is_connected:
        logger.error("Cannot start grabbing: not connected")
        return False
    
    try:
        logger.info("Starting grabbing...")
        self.mvsdk.CameraPlay(self._handle)
        self._is_grabbing = True
        return True
    except Exception as e:
        logger.error(f"Failed to start grabbing: {e}", exc_info=True)
        return False
```

### Step 7: Implement stop_grabbing()

```python
def stop_grabbing(self) -> bool:
    """Dừng grab"""
    if not self._is_grabbing:
        return True
    
    try:
        logger.info("Stopping grabbing...")
        self.mvsdk.CameraPause(self._handle)
        self._is_grabbing = False
        return True
    except Exception as e:
        logger.error(f"Failed to stop grabbing: {e}", exc_info=True)
        return False
```

### Step 8: Implement capture_frame()

```python
def capture_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
    """Chụp frame"""
    if not self._is_connected or not self._is_grabbing:
        logger.error("Cannot capture: camera not ready")
        return None
    
    pFrameBuffer = None
    pRawData = None
    
    try:
        # Get raw frame
        pRawData, FrameHead = self.mvsdk.CameraGetImageBuffer(self._handle, timeout_ms)
        
        # Allocate buffer for processed frame
        pFrameBuffer = self.mvsdk.CameraAlignMalloc(
            FrameHead.iWidth * FrameHead.iHeight * 3, 16
        )
        
        # Process image (Bayer -> RGB or keep Mono)
        self.mvsdk.CameraImageProcess(self._handle, pRawData, pFrameBuffer, FrameHead)
        
        # Convert to NumPy array
        if FrameHead.uiMediaType == self.mvsdk.CAMERA_MEDIA_TYPE_MONO8:
            # Grayscale
            frame_data = (self.mvsdk.c_ubyte * FrameHead.iWidth * FrameHead.iHeight).from_address(pFrameBuffer)
            image = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                (FrameHead.iHeight, FrameHead.iWidth)
            )
        else:
            # RGB
            frame_data = (self.mvsdk.c_ubyte * FrameHead.iWidth * FrameHead.iHeight * 3).from_address(pFrameBuffer)
            image = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                (FrameHead.iHeight, FrameHead.iWidth, 3)
            )
        
        # Copy data (important!)
        image = image.copy()
        
        return image
        
    except Exception as e:
        logger.error(f"Failed to capture frame: {e}", exc_info=True)
        return None
        
    finally:
        # CRITICAL: Always release buffers
        if pRawData is not None:
            try:
                self.mvsdk.CameraReleaseImageBuffer(self._handle, pRawData)
            except:
                pass
        
        if pFrameBuffer is not None:
            try:
                self.mvsdk.CameraAlignFree(pFrameBuffer)
            except:
                pass
```

### Step 9: Implement set_parameter()

```python
def set_parameter(self, param_name: str, value: Any) -> bool:
    """Set parameter"""
    if not self._is_connected:
        return False
    
    try:
        logger.info(f"Setting {param_name} = {value}")
        
        if param_name == 'ExposureTime':
            self.mvsdk.CameraSetExposureTime(self._handle, value)
        elif param_name == 'Gain':
            self.mvsdk.CameraSetAnalogGain(self._handle, value)
        elif param_name == 'TriggerMode':
            mode = 1 if value == 'on' else 0
            self.mvsdk.CameraSetTriggerMode(self._handle, mode)
        else:
            logger.warning(f"Unknown parameter: {param_name}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to set parameter: {e}", exc_info=True)
        return False
```

## 5. Testing

### 5.1 Test với Mock Camera trước

```bash
# Đảm bảo camera.yaml có:
# type: "mock"

python test_run.py
python main.py
```

### 5.2 Chuyển sang MindVision

```yaml
# camera.yaml
camera:
  type: "mindvision"
  ip: "192.168.1.41"
```

### 5.3 Test kết nối

```bash
python test_run.py
```

### 5.4 Test UI

```bash
python main.py
```

## 6. Troubleshooting

### SDK không import được

```python
# Check SDK path
import sys
sys.path.append('C:/Program Files/MindVision/SDK/Python')
import mvsdk
```

### Camera không tìm thấy

1. Ping camera: `ping 192.168.1.41`
2. Check với MVS Viewer
3. Check firewall
4. Check network adapter settings

### Device Busy

- Đóng MVS Viewer
- Đóng tất cả app khác
- Reboot camera

### Frame timeout

- Tăng timeout: `grab_timeout: 2000` trong camera.yaml
- Check camera streaming
- Check network bandwidth

## 7. Performance Tuning

### 7.1 Frame Rate

```yaml
frame_rate: 30  # Adjust based on needs
```

### 7.2 Image Size

```yaml
width: 1280
height: 1024
```

Giảm resolution để tăng FPS.

### 7.3 Pixel Format

```yaml
pixel_format: "Mono8"  # Faster than RGB
```

### 7.4 Exposure Time

```yaml
exposure_time: 10000  # Balance between brightness and speed
```

## 8. Next Steps

Sau khi integrate thành công:

1. Test với các exposure settings khác nhau
2. Test trigger mode
3. Implement reconnect logic
4. Add image save functionality
5. Integrate QR decoder

---

**Note**: Code examples trên dựa trên MindVision SDK documentation. Chi tiết API có thể khác nhau tùy phiên bản SDK. Tham khảo SDK documentation chính thức.

