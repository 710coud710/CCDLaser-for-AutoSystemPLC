# ✅ Camera Setup - Chỉ MindVision Camera

## 🎯 Đã làm gì?

### Loại bỏ hoàn toàn Mock Camera

✅ **Xóa** `app/model/camera/mock_camera.py`  
✅ **Xóa** tất cả references đến MockCamera  
✅ **Đơn giản hóa** CameraConnectionService  
✅ **Cập nhật** config chỉ cho MindVision  

## 📁 Files đã thay đổi

### 1. Đã xóa:
```
❌ app/model/camera/mock_camera.py
```

### 2. Đã cập nhật:

#### `app/model/camera/__init__.py`
```python
# Trước:
from .mock_camera import MockCamera
__all__ = [..., 'MockCamera', ...]

# Sau:
# Không import MockCamera nữa
__all__ = ['CameraBase', 'CameraConnectionService', 'MindVisionCamera']
```

#### `app/model/camera/camera_connection_service.py`
```python
# Trước:
def create_camera(self, camera_type: str, camera_id: str, config):
    if camera_type == 'mock':
        self._camera = MockCamera(...)
    elif camera_type == 'mindvision':
        self._camera = MindVisionCamera(...)

# Sau:
def create_camera(self, camera_id: str, config):
    # Chỉ tạo MindVision camera
    self._camera = MindVisionCamera(camera_id, config)
```

#### `app/presenter/main_presenter.py`
```python
# Trước:
camera_type = camera_config.get('type', 'mock')
self._camera_service.create_camera(camera_type, camera_id, config)

# Sau:
camera_id = camera_config.get('ip', 'cam2')
self._camera_service.create_camera(camera_id, config)
```

#### `setting/camera.yaml`
```yaml
# Trước:
camera:
  type: "mindvision"  # hoặc "mock"
  ip: "cam2"

# Sau:
camera:
  # Không có field "type" nữa - chỉ MindVision
  ip: "cam2"  # Camera ID
```

## 🚀 Cách sử dụng

### Config camera trong `setting/camera.yaml`:

```yaml
camera:
  # Camera ID - chọn camera nào?
  ip: "cam2"    # Camera thứ 2 (index 1)
  # Hoặc:
  # ip: "cam0"  # Camera đầu tiên
  # ip: "cam1"  # Camera thứ 2
  # ip: "auto"  # Tự động chọn camera đầu
  # ip: "CB12345678"  # Chọn theo Serial Number
  
  # Camera parameters
  exposure_time: 30000  # 30ms
  gain: 0
  trigger_mode: "off"   # continuous mode
  pixel_format: "Mono8"
```

### Chạy app:

```bash
cd D:\Beta\CCDLaser
python main.py
```

**App sẽ tự động:**
1. Load mvsdk
2. Enumerate cameras
3. Chọn camera theo ID trong config
4. Kết nối và cấu hình
5. Sẵn sàng stream

## 📊 Kiến trúc đơn giản hơn

### Trước (có Mock):
```
CameraConnectionService
    ├─ MockCamera (test)
    └─ MindVisionCamera (production)
```

### Sau (chỉ MindVision):
```
CameraConnectionService
    └─ MindVisionCamera (chỉ camera thật)
```

## ✨ Lợi ích

### 1. Code đơn giản hơn
- ✅ Ít file hơn
- ✅ Ít logic branching
- ✅ Dễ maintain

### 2. Config rõ ràng hơn
- ✅ Không cần field `type`
- ✅ Chỉ config cho camera thật
- ✅ Ít confusion

### 3. Performance tốt hơn
- ✅ Không có overhead của factory pattern
- ✅ Direct instantiation

## 🔧 API Changes

### CameraConnectionService

#### Trước:
```python
service.create_camera(
    camera_type="mindvision",  # ← Phải chỉ định type
    camera_id="cam2",
    config={...}
)
```

#### Sau:
```python
service.create_camera(
    camera_id="cam2",  # ← Không cần type nữa
    config={...}
)
```

## 📝 Camera ID Options

Trong `setting/camera.yaml`, field `ip` có thể là:

| Giá trị | Ý nghĩa |
|---------|---------|
| `"cam0"` | Camera đầu tiên (index 0) |
| `"cam1"` | Camera thứ 2 (index 1) |
| `"cam2"` | Camera thứ 3 (index 2) |
| `"0"`, `"1"`, `"2"` | Index trực tiếp |
| `"auto"` | Tự động chọn camera đầu tiên |
| `"CB12345678"` | Chọn theo Serial Number |

## 🐛 Troubleshooting

### Lỗi: "No camera found"

**Nguyên nhân**: Không có camera MindVision nào

**Giải pháp**:
1. Check camera đã cắm USB chưa
2. Check trong Device Manager
3. Reboot camera
4. Cài driver MindVision

---

### Lỗi: "Camera index out of range"

**Nguyên nhân**: Config `ip: "cam2"` nhưng chỉ có 1 camera

**Giải pháp**:
- Đổi thành `ip: "cam0"` hoặc `ip: "auto"`

---

### Lỗi: "Cannot import mvsdk"

**Nguyên nhân**: File `mvsdk.py` không có trong project root

**Giải pháp**:
- Đảm bảo `mvsdk.py` ở `D:\Beta\CCDLaser\mvsdk.py`

## 📖 Documentation

Các file hướng dẫn:
- `docs/camera-spec.md` - Camera integration spec
- `docs/mindvision-integration.md` - SDK integration guide
- `grab.py` - Example code từ SDK

## 🎓 Summary

### Đã loại bỏ:
- ❌ Mock camera
- ❌ Camera type selection
- ❌ Factory pattern complexity

### Giữ lại:
- ✅ MindVision camera only
- ✅ Simple, direct instantiation
- ✅ Clean configuration

### Kết quả:
- 🚀 Code đơn giản hơn
- 🎯 Tập trung vào camera thật
- 📦 Dễ deploy và maintain

---

**Status**: ✅ Production ready - Chỉ MindVision camera

**Version**: 2.0.0 (Simplified)

**Last Updated**: 2025-12-24

