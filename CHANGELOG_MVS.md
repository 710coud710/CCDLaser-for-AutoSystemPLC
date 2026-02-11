# MVS Camera Integration - Changelog

## [2026-02-11] - MVS SDK Integration

### Added

#### 1. New Camera Implementation
- **`app/model/camera/mvs_camera.py`** - MVS Camera class theo Hikvision SDK
  - Flow kết nối đầy đủ: Initialize → Enumerate → Create Handle → Open → Config → Start
  - Hỗ trợ GigE và USB camera
  - Auto-detect và optimize packet size (GigE)
  - Xử lý Bayer pattern conversion
  - Proper buffer management với release

#### 2. Multi-Camera Support
- **`app/model/camera/camera_connection_service.py`** - Updated để hỗ trợ cả 2 SDK
  - Tự động chọn camera type từ config
  - Factory pattern: tạo MindVision hoặc MVS camera
  - Unified interface cho Presenter layer

#### 3. Configuration
- **`setting/camera.yaml`** - Thêm `camera_type` option
  ```yaml
  camera_type: "mvs"  # "mindvision" hoặc "mvs"
  ```

#### 4. Testing
- **`test_mvs_camera.py`** - Test script đầy đủ
  - Test connection flow
  - Capture test frames
  - Log chi tiết từng bước

#### 5. Documentation
- **`docs/MVS-Camera-Integration.md`** - Hướng dẫn chi tiết
  - Flow diagram
  - API comparison
  - Troubleshooting guide
  - Code examples

### Modified

- **`app/model/camera/__init__.py`** - Export MVSCamera class
- **`setting/camera.yaml`** - Cập nhật comments và thêm camera_type

### Technical Details

#### MVS Connection Flow
```
[1] Initialize SDK
[2] Enumerate Devices
[2.1] Select Camera (by ID/index/SN)
[3] Create Handle
[4] Open Device (Exclusive access)
[5] Optimize Packet Size (GigE)
[6] Configure Parameters (Exposure, Gain, Trigger)
[7] Start Grabbing
```

#### Supported Features
- ✓ GigE và USB camera
- ✓ Auto packet size optimization
- ✓ Mono8 và RGB8 pixel formats
- ✓ Bayer pattern auto-conversion
- ✓ Software trigger mode
- ✓ Continuous (free-run) mode
- ✓ Parameter get/set (Exposure, Gain, Gamma, FrameRate)
- ✓ Error handling với hex error codes

#### Dependencies
- MVS SDK Runtime (Win64_x64)
- MvImport folder với Python bindings:
  - MvCameraControl_class.py
  - CameraParams_header.py
  - MvErrorDefine_const.py
  - PixelType_header.py

### Usage

#### Quick Start

1. **Cấu hình camera type** trong `setting/camera.yaml`:
   ```yaml
   camera:
     camera_type: "mvs"  # Chuyển sang MVS
     ip: "0"  # Camera index
   ```

2. **Chạy test**:
   ```bash
   python test_mvs_camera.py
   ```

3. **Chạy app**:
   ```bash
   python main.py
   ```

#### Switching Between SDKs

**MindVision:**
```yaml
camera_type: "mindvision"
```

**MVS (Hikvision):**
```yaml
camera_type: "mvs"
```

Không cần thay đổi code, chỉ restart app.

### Backward Compatibility

- ✓ Không breaking changes
- ✓ MindVision SDK vẫn hoạt động bình thường
- ✓ Default vẫn là MindVision (nếu không set camera_type)
- ✓ Tất cả existing code không cần sửa

### Known Issues & Limitations

1. **MVS SDK yêu cầu:**
   - Python 64-bit
   - MVS Runtime trong PATH
   - Admin rights (có thể cần cho GigE)

2. **Chưa implement:**
   - ROI (Region of Interest)
   - Hardware trigger
   - Multi-camera simultaneous capture
   - Image save/recording

3. **Testing status:**
   - ⚠️ Chưa test với camera thực tế
   - ⚠️ Chưa test multi-camera
   - ⚠️ Chưa benchmark performance

### Next Steps

1. [ ] Test với MVS camera thực tế
2. [ ] Verify GigE packet size optimization
3. [ ] Test multi-camera setup
4. [ ] Implement ROI nếu cần
5. [ ] Performance comparison với MindVision
6. [ ] Add hardware trigger support (nếu cần)

### References

- Tutorial: `docs/MVS-tutorial.md`
- Integration guide: `docs/MVS-Camera-Integration.md`
- BasicDemo reference: `Python/AreaScanCamera/BasicDemo/`
- MVS bindings: `MvImport/`

---

**Migration Path:**
```
Hiện tại: MindVision SDK (mvsdk.py)
          ↓
Tương lai: MVS SDK (MvCameraControl)
          ↓
Cả hai SDK đều được support
Chọn qua config.yaml
```
