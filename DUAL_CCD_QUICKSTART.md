# Dual CCD System - Hướng Dẫn Nhanh

## Tổng Quan
Hệ thống mới cho phép chạy **2 camera hoàn toàn độc lập** trong 2 threads riêng biệt.

## Chạy Hệ Thống

### Windows (PowerShell):
```powershell
.\run_dual_ccd.ps1
```

### Windows (CMD):
```cmd
run_dual_ccd.bat
```

### Hoặc chạy trực tiếp:
```bash
python main_dual_ccd.py
```

## Giao Diện

```
+------------------------------------+------------------------------------+
|            CCD1 View              |            CCD2 View              |
+------------------------------------+------------------------------------+
|  [Image Display Area]             |  [Image Display Area]             |
|                                    |                                    |
|  CCD1: Not started                 |  CCD2: Not started                 |
|                                    |                                    |
|  [Start CCD1] [Stop CCD1]         |  [Start CCD2] [Stop CCD2]         |
|                                    |                                    |
|  [Status Messages]                 |  [Status Messages]                 |
+------------------------------------+------------------------------------+
```

## Sử Dụng

### 1. Khởi Động CCD1:
- Click nút **"Start CCD1"**
- Camera CCD1 sẽ connect và streaming
- Ảnh hiển thị bên trái

### 2. Khởi Động CCD2:
- Click nút **"Start CCD2"**
- Camera CCD2 sẽ connect và streaming
- Ảnh hiển thị bên phải

### 3. Dừng Camera:
- Click **"Stop CCD1"** hoặc **"Stop CCD2"**
- Camera sẽ dừng streaming và disconnect

## Cấu Hình

File: `setting/camera.yaml`

```yaml
# CCD1 - Camera index 0
camera_ccd1:
  ip: "0"              # Camera index
  mono_mode: 1         # 1=Mono, 0=RGB
  exposure_time: 10000
  gain: 0
  # ... other settings

# CCD2 - Camera index 1
camera_ccd2:
  ip: "1"              # Camera index
  mono_mode: 1         # 1=Mono, 0=RGB
  exposure_time: 10000
  gain: 0
  # ... other settings
```

### Tham Số Quan Trọng:

- **ip**: Camera index ("0", "1", "2") hoặc serial number
- **mono_mode**: 
  - `1` = Mono8 (grayscale)
  - `0` = RGB8 (color)
- **exposure_time**: Thời gian phơi sáng (microseconds)
- **gain**: Gain value (dB)
- **flip_horizontal**: `true` để mirror ảnh

## Logs

Logs được ghi vào:
- Console
- File: `logs/app.log`

Prefix để phân biệt:
- `[CCD1]` - Messages từ CCD1
- `[CCD2]` - Messages từ CCD2

## Troubleshooting

### Camera không connect?
1. Kiểm tra camera index trong `camera.yaml`
2. Kiểm tra camera có được cắm vào
3. Xem logs để biết lỗi chi tiết

### Chỉ 1 camera hoạt động?
- Đảm bảo 2 camera có `ip` (index) khác nhau
- CCD1 dùng `ip: "0"`
- CCD2 dùng `ip: "1"`

### Ảnh bị ngược?
- Bật `flip_horizontal: true` trong config

### Thread bị treo?
- Click nút Stop
- Đợi 3 giây
- Nếu vẫn treo, tắt ứng dụng và chạy lại

## Kiến Trúc

Mỗi CCD có:
- **Model**: `CCD1CameraService` / `CCD2CameraService` (QThread)
- **View**: `CCD1View` / `CCD2View`
- **Presenter**: `CCD1Presenter` / `CCD2Presenter`

→ **Hoàn toàn độc lập**, không ảnh hưởng lẫn nhau!

## So Sánh vs Kiến Trúc Cũ

| Feature | Cũ (main.py) | Mới (main_dual_ccd.py) |
|---------|-------------|------------------------|
| CCD support | 1 main + 1 worker | 2 hoàn toàn độc lập |
| Threading | Shared logic | 2 threads riêng |
| Isolation | Weak | Strong |
| Extensibility | Hard | Easy |

## Development

### Thêm chức năng cho CCD1:
```
app/ccd1/
  ├── model/ccd1_camera_service.py  ← Thêm logic xử lý
  ├── view/ccd1_view.py              ← Thêm UI controls
  └── presenter/ccd1_presenter.py    ← Thêm event handlers
```

### Thêm chức năng cho CCD2:
```
app/ccd2/
  ├── model/ccd2_camera_service.py  ← Thêm logic xử lý
  ├── view/ccd2_view.py              ← Thêm UI controls
  └── presenter/ccd2_presenter.py    ← Thêm event handlers
```

### Shared components:
```
app/shared/
  ├── model/camera/                  ← Camera base classes
  └── view/image_display_widget.py   ← Shared widgets
```

## Xem Thêm

- [Chi tiết kiến trúc](docs/dual-ccd-architecture.md)
- [Spec camera](docs/camera-spec.md)
- [Project spec](docs/project-spec.md)
