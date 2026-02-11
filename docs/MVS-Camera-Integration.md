# MVS Camera Integration Guide

## Tổng quan

Dự án CCDLaser đã được nâng cấp để hỗ trợ **2 loại camera SDK**:

1. **MindVision SDK** (mvsdk.py) - SDK gốc đang dùng
2. **MVS SDK** (Hikvision MvCameraControl) - SDK mới tích hợp

## Cấu trúc Code

### 1. Camera Classes

```
app/model/camera/
├── camera_base.py              # Abstract base class
├── mindvision_camera.py        # MindVision implementation (mvsdk)
├── mvs_camera.py              # MVS implementation (Hikvision) ← MỚI
└── camera_connection_service.py # Factory service (chọn camera type)
```

### 2. MVS SDK Files

```
MvImport/                       # MVS SDK Python bindings
├── MvCameraControl_class.py   # Main camera control
├── CameraParams_header.py     # Parameter definitions
├── MvErrorDefine_const.py     # Error codes
└── PixelType_header.py        # Pixel format definitions
```

### 3. BasicDemo Reference

```
Python/AreaScanCamera/BasicDemo/
├── BasicDemo.py               # GUI demo
└── CamOperation_class.py      # Camera operations reference
```

## Cách Kết Nối MVS Camera

### Flow Kết Nối (theo tutorial)

```
[1] Initialize SDK
    ↓
[2] Enumerate Devices (tìm camera)
    ↓
[2.1] Select Camera (theo ID/index)
    ↓
[3] Create Handle
    ↓
[4] Open Device
    ↓
[5] Optimize Packet Size (GigE only)
    ↓
[6] Configure Parameters (Exposure, Gain, Trigger...)
    ↓
[7] Start Grabbing
    ↓
[8] Capture Frames (MV_CC_GetImageBuffer)
    ↓
[9] Stop Grabbing
    ↓
[10] Close Device & Destroy Handle
```

### Code Example

```python
from app.model.camera import CameraConnectionService

# Create service
camera_service = CameraConnectionService()

# Create MVS camera (camera_type='mvs' in config)
config = {
    'camera_type': 'mvs',  # ← Chọn MVS SDK
    'exposure_time': 30000,
    'gain': 0,
    'trigger_mode': 'off'
}

camera_service.create_camera('cam0', config)

# Connect
camera_service.connect()

# Start streaming
camera_service.start_streaming()

# Capture frame
frame = camera_service.get_frame(timeout_ms=1000)

# Cleanup
camera_service.stop_streaming()
camera_service.disconnect()
```

## Cấu Hình

### File: `setting/camera.yaml`

```yaml
camera:
  # Camera Type - QUAN TRỌNG!
  camera_type: "mvs"  # "mindvision" hoặc "mvs"
  
  # Camera ID
  ip: "0"  # hoặc "cam0", "auto", "CB12345678" (SN)
  
  # Parameters
  exposure_time: 30000  # microseconds
  gain: 0
  trigger_mode: "off"
  pixel_format: "auto"  # auto, mono8, rgb8
```

### Camera Type Options

| camera_type | SDK | Description |
|------------|-----|-------------|
| `mindvision` | mvsdk.py | MindVision SDK (mặc định cũ) |
| `mvs` | MvCameraControl | Hikvision MVS SDK (mới) |

## API Comparison

### MindVision vs MVS

| Operation | MindVision | MVS |
|-----------|------------|-----|
| Enumerate | `CameraEnumerateDevice()` | `MV_CC_EnumDevices()` |
| Init | `CameraInit()` | `MV_CC_CreateHandle()` + `MV_CC_OpenDevice()` |
| Start | `CameraPlay()` | `MV_CC_StartGrabbing()` |
| Get Frame | `CameraGetImageBuffer()` | `MV_CC_GetImageBuffer()` |
| Release | `CameraReleaseImageBuffer()` | `MV_CC_FreeImageBuffer()` |
| Stop | `CameraPause()` | `MV_CC_StopGrabbing()` |
| Close | `CameraUnInit()` | `MV_CC_CloseDevice()` + `MV_CC_DestroyHandle()` |

### Parameter Names

| Parameter | MindVision | MVS |
|-----------|------------|-----|
| Exposure | `CameraSetExposureTime()` | `MV_CC_SetFloatValue("ExposureTime")` |
| Gain | `CameraSetAnalogGain()` | `MV_CC_SetFloatValue("Gain")` |
| Trigger | `CameraSetTriggerMode()` | `MV_CC_SetEnumValue("TriggerMode")` |

## Testing

### Test Script

Chạy test kết nối MVS camera:

```bash
python test_mvs_camera.py
```

Script này sẽ:
1. Tạo camera instance (MVS)
2. Kết nối camera
3. Start grabbing
4. Capture 5 frames
5. Stop và disconnect
6. Log chi tiết từng bước

### Expected Output

```
[Step 1] Creating camera service...
[Step 2] Creating MVS camera instance...
[Step 3] Connecting to camera...
  [1/7] Initializing MVS SDK...
  [2/7] Enumerating devices...
  Found 1 camera(s)
  [2.1] Selecting camera...
  [3/7] Creating camera handle...
  [4/7] Opening device...
  [5/7] Optimizing packet size for GigE...
  [6/7] Configuring camera parameters...
  [7/7] Ready
✓✓ MVS Camera connected successfully
```

## Troubleshooting

### 1. Không tìm thấy camera

```
Error: No MVS camera found
```

**Giải pháp:**
- Kiểm tra camera đã cắm điện + LAN
- Ping IP camera (nếu GigE)
- Tắt firewall
- Chạy MVS Viewer để test camera riêng

### 2. DLL load failed

```
ImportError: DLL load failed
```

**Giải pháp:**
- Thêm MVS Runtime vào PATH:
  ```
  C:\Program Files\MVS\Runtime\Win64_x64
  ```
- Restart máy sau khi thêm PATH
- Đảm bảo Python 64-bit

### 3. Open device failed

```
Error: Open device failed: 0x80000200
```

**Giải pháp:**
- Camera đang bị app khác dùng
- Đóng MVS Viewer hoặc app khác
- Restart camera (rút nguồn)

### 4. GetImageBuffer timeout

```
Warning: Frame timeout (1000ms)
```

**Giải pháp:**
- Tăng timeout: `get_frame(timeout_ms=2000)`
- Kiểm tra trigger mode (nên dùng 'off' cho free-run)
- Kiểm tra packet size (GigE)

## Main Application Integration

Ứng dụng chính (`main.py`) tự động sử dụng config từ `camera.yaml`:

```python
# main.py
# Camera service tự động đọc camera_type từ config
# Không cần thay đổi code, chỉ cần sửa camera.yaml
```

### Chuyển đổi giữa MindVision và MVS

Chỉ cần sửa 1 dòng trong `setting/camera.yaml`:

```yaml
# Dùng MindVision
camera_type: "mindvision"

# Dùng MVS
camera_type: "mvs"
```

Restart ứng dụng để áp dụng.

## Performance Notes

### MVS SDK
- **Ưu điểm:**
  - Hỗ trợ đầy đủ tính năng camera Hikvision
  - Tối ưu packet size tự động cho GigE
  - API rõ ràng, có error code chi tiết
  
- **Nhược điểm:**
  - Phụ thuộc MVS Runtime
  - Chỉ 64-bit
  - Cần thêm PATH environment

### MindVision SDK
- **Ưu điểm:**
  - Nhẹ, không phụ thuộc nhiều
  - API đơn giản
  
- **Nhược điểm:**
  - Ít tài liệu
  - Chỉ hỗ trợ MindVision camera

## References

### Documentation
- [MVS-tutorial.md](./MVS-tutorial.md) - Hướng dẫn chi tiết MVS SDK
- [BasicDemo](../Python/AreaScanCamera/BasicDemo/) - Code tham khảo từ Hikvision

### SDK Files
- MvImport/ - MVS Python bindings
- Python/AreaScanCamera/ - Official samples

## Summary

### Điểm Khác Biệt Chính

| Aspect | MindVision | MVS |
|--------|------------|-----|
| Enum | 1 API call | 1 API call |
| Init | 1 call (CameraInit) | 2 calls (Create + Open) |
| Frame | Get → Process → Release | Get → Release |
| Packet Size | Manual | Auto-detect (GigE) |
| Error Handling | Exception | Return codes |

### Best Practices

1. **Always check return codes** (MVS)
2. **Always release buffers** (cả 2)
3. **Copy frame data** trước khi release
4. **Stop grabbing** trước khi disconnect
5. **Cleanup properly** khi thoát app

## Next Steps

1. Test với camera thực tế
2. Verify packet size optimization (GigE)
3. Test với multi-camera setup
4. Benchmark performance vs MindVision

---

**Author:** CCDLaser Development Team  
**Date:** 2026-02-11  
**Version:** 1.0
