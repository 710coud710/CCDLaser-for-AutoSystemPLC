# MVS Camera - Quick Start Guide

## 🚀 Bắt Đầu Nhanh

### Bước 1: Kiểm tra MVS SDK

Đảm bảo đã cài MVS SDK và thêm vào PATH:

```
C:\Program Files\MVS\Runtime\Win64_x64
```

### Bước 2: Kiểm tra thư viện Python

Đảm bảo có folder `MvImport/` trong project root với các file:
- ✓ MvCameraControl_class.py
- ✓ CameraParams_header.py
- ✓ MvErrorDefine_const.py
- ✓ PixelType_header.py

### Bước 3: Cấu hình Camera

Mở `setting/camera.yaml`, sửa dòng:

```yaml
camera:
  camera_type: "mvs"  # ← Chuyển sang MVS SDK
  ip: "0"             # ← Camera index (0, 1, 2...) hoặc "auto"
```

### Bước 4: Test Kết Nối

```bash
python test_mvs_camera.py
```

Nếu thấy:
```
✓✓✓ Camera connected successfully
✓✓✓ All tests passed!
```

→ Thành công!

### Bước 5: Chạy App

```bash
python main.py
```

## 🔄 Chuyển Đổi SDK

### Dùng MVS (Hikvision)
```yaml
camera_type: "mvs"
```

### Dùng MindVision
```yaml
camera_type: "mindvision"
```

**Chỉ cần sửa config và restart!**

## 📋 Flow Kết Nối MVS

```
Initialize SDK
    ↓
Enumerate (tìm camera)
    ↓
Select Camera (theo index/SN)
    ↓
Create Handle
    ↓
Open Device
    ↓
Optimize Packet (GigE)
    ↓
Config Parameters
    ↓
Start Grabbing
    ↓
Capture Frames ✓
```

## ⚙️ Config Quan Trọng

```yaml
camera:
  camera_type: "mvs"        # ← QUAN TRỌNG!
  ip: "0"                   # Camera index
  exposure_time: 30000      # 30ms (microseconds)
  gain: 0                   # 0 dB
  trigger_mode: "off"       # Free-run
  pixel_format: "auto"      # auto/mono8/rgb8
```

## 🐛 Troubleshooting

### ⚠️ DLL load failed (QUAN TRỌNG!)
```
FileNotFoundError: Could not find module 'MvCameraControl.dll'
```

**Nguyên nhân:**
- Chỉ có file `MvCameraControl.dll` KHÔNG ĐỦ!
- Cần toàn bộ MVS Runtime với 40+ DLL dependencies

**Fix:**

**Option 1: Cài MVS SDK đầy đủ (KHUYÊN DÙNG)**
```
1. Download MVS SDK từ Hikvision
2. Cài đặt MVS SDK
3. Thêm PATH: C:\Program Files\MVS\Runtime\Win64_x64
4. RESTART MÁY
5. Run: python check_mvs_dependencies.py
```

**Option 2: Copy toàn bộ Runtime folder**
```
1. Copy: C:\Program Files\MVS\Runtime\Win64_x64\
2. Paste vào: D:\Beta\CCDLaser\mvs_runtime\
3. Phải copy TẤT CẢ files (40+ DLL)!
```

**Option 3: Dùng MindVision thay thế**
```yaml
# setting/camera.yaml
camera_type: "mindvision"  # Fallback
```

**Chi tiết:** Xem [docs/MVS-DLL-Problem-Solution.md](docs/MVS-DLL-Problem-Solution.md)

### Kiểm tra dependencies

```bash
python check_mvs_dependencies.py
```

Script này sẽ check:
- ✓ Python 64-bit
- ✓ MVS Runtime installed
- ✓ DLL files exists
- ✓ PATH configured
- ✓ Import test

### Không tìm thấy camera
```
Error: No MVS camera found
```

**Fix:**
1. Kiểm tra camera đã cắm điện + LAN
2. Ping IP camera (nếu GigE)
3. Tắt firewall
4. Mở MVS Viewer để test

### Open device failed
```
Error: 0x80000200
```

**Fix:**
1. Đóng MVS Viewer
2. Đóng app khác đang dùng camera
3. Restart camera (rút nguồn)

### Frame timeout
```
Warning: Frame timeout
```

**Fix:**
1. Sửa `trigger_mode: "off"` (free-run)
2. Tăng timeout: `grab_timeout: 2000`
3. Kiểm tra packet size (GigE)

## 📚 Tài Liệu

- **Chi tiết:** [docs/MVS-Camera-Integration.md](docs/MVS-Camera-Integration.md)
- **Tutorial:** [docs/MVS-tutorial.md](docs/MVS-tutorial.md)
- **Changelog:** [CHANGELOG_MVS.md](CHANGELOG_MVS.md)
- **BasicDemo:** `Python/AreaScanCamera/BasicDemo/`

## ✅ Checklist

Trước khi chạy:

- [ ] MVS SDK đã cài
- [ ] PATH đã thêm
- [ ] Python 64-bit
- [ ] MvImport/ có đầy đủ file
- [ ] camera.yaml đã config camera_type
- [ ] Camera đã cắm điện + LAN (GigE)
- [ ] Test script chạy OK

## 🎯 API Example

```python
from app.model.camera import CameraConnectionService

# Create service
service = CameraConnectionService()

# Create camera (auto-detect type from config)
config = {
    'camera_type': 'mvs',
    'exposure_time': 30000,
    'gain': 0
}
service.create_camera('0', config)

# Connect
service.connect()

# Start
service.start_streaming()

# Get frame
frame = service.get_frame(timeout_ms=1000)

# Stop
service.stop_streaming()
service.disconnect()
service.cleanup()
```

## 🔧 Camera ID Options

```yaml
ip: "0"              # Index 0
ip: "1"              # Index 1
ip: "cam0"           # Index 0
ip: "auto"           # First camera
ip: "CB12345678"     # Serial Number
```

## 📊 Comparison

| Feature | MindVision | MVS |
|---------|-----------|-----|
| SDK | mvsdk.py | MvCameraControl |
| GigE Auto Packet | ❌ | ✓ |
| Error Detail | ⚠️ | ✓✓ |
| Bayer Convert | Manual | Auto |
| Documentation | ⚠️ | ✓✓ |

## 🎉 Xong!

Nếu test script pass → camera đã sẵn sàng cho production!

```bash
python test_mvs_camera.py  # ✓
python main.py             # ✓
```

---

**Questions?** 
- Check: [docs/MVS-Camera-Integration.md](docs/MVS-Camera-Integration.md)
- Reference: `Python/AreaScanCamera/BasicDemo/`
