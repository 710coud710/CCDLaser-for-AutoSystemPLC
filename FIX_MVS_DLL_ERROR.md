# 🔴 Sửa Lỗi: MvCameraControl.dll NOT FOUND

## ❌ Lỗi Bạn Gặp

```
FileNotFoundError: Could not find module 'MvCameraControl.dll' 
(or one of its dependencies)
```

## 💡 Nguyên Nhân

**Chỉ có file `MvCameraControl.dll` trong folder KHÔNG ĐỦ!**

File này cần **40+ DLL khác** (dependencies):
- MVGigEVisionSDK.dll
- MVUSB3VisionSDK.dll
- ImageConvert.dll
- MediaProcess.dll
- log4cpp_D.dll
- ... và nhiều DLL khác

→ **Phải có TOÀN BỘ MVS Runtime!**

---

## ✅ Giải Pháp (Chọn 1 trong 3)

### 🎯 Giải Pháp 1: Cài MVS SDK Đầy Đủ (KHUYÊN DÙNG)

#### Bước 1: Download MVS SDK

Vào: https://www.hikrobotics.com/en/machinevision/service/download

Tìm: **MVS (Machine Vision Software)** → Windows 64-bit

Download file: `MVS_xxx_Win64.exe` (~500MB)

#### Bước 2: Cài Đặt

```
1. Chạy file cài đặt
2. Chọn "Typical" installation
3. Path: C:\Program Files\MVS\
4. Next → Next → Install
5. Hoàn tất
```

#### Bước 3: Thêm vào PATH

**Cách 1: GUI**
```
1. Mở Control Panel
2. System → Advanced system settings
3. Environment Variables
4. System variables → Path → Edit → New
5. Thêm: C:\Program Files\MVS\Runtime\Win64_x64
6. OK → OK → OK
7. ⚠️ RESTART MÁY!
```

**Cách 2: PowerShell (Admin)**
```powershell
# Copy paste lệnh này (PowerShell as Admin):
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\MVS\Runtime\Win64_x64",
    [EnvironmentVariableTarget]::Machine
)
# Sau đó RESTART MÁY!
```

#### Bước 4: Kiểm Tra

```bash
# Restart máy xong, chạy:
python check_mvs_dependencies.py
```

Nếu thấy tất cả ✓ → OK!

---

### 🔧 Giải Pháp 2: Copy Runtime Folder (Portable)

Nếu không thể cài MVS (không có admin, offline...):

#### Bước 1: Lấy folder từ máy khác

Từ máy đã cài MVS, copy **TOÀN BỘ** folder:
```
C:\Program Files\MVS\Runtime\Win64_x64\
```

**Quan trọng:** Phải copy **TẤT CẢ** files trong folder này!
(Khoảng 40-50 file DLL, tổng ~200MB)

#### Bước 2: Paste vào project

```
D:\Beta\CCDLaser\
    └── mvs_runtime\           ← Tạo folder mới
        ├── MvCameraControl.dll
        ├── MVGigEVisionSDK.dll
        ├── MVUSB3VisionSDK.dll
        └── ... (ALL DLL files)
```

#### Bước 3: Code tự động tìm

Script đã được update để tự động tìm DLL trong folder `mvs_runtime/`

Không cần làm gì thêm!

#### Bước 4: Kiểm tra

```bash
python check_mvs_dependencies.py
```

---

### 🔄 Giải Pháp 3: Dùng MindVision Thay Thế

Nếu không thể dùng MVS SDK:

#### Bước 1: Sửa config

Mở file: `setting/camera.yaml`

Sửa dòng:
```yaml
camera:
  camera_type: "mindvision"  # ← Đổi từ "mvs" sang "mindvision"
```

#### Bước 2: Restart app

```bash
python main.py
```

→ App sẽ dùng MindVision SDK (không có vấn đề DLL)

---

## 🔍 Kiểm Tra Sau Khi Fix

### Test 1: Check Dependencies

```bash
python check_mvs_dependencies.py
```

Expected output:
```
✓ Python 64-bit OK
✓ Found MVS Runtime
✓ All DLLs found
✓ MVS Runtime is in PATH
✓ Import SUCCESS!
✓✓✓ ALL CHECKS PASSED!
```

### Test 2: Test Camera Connection

```bash
python test_mvs_camera.py
```

Expected:
```
[INFO] Connecting to camera...
[INFO] Enumerating devices...
[INFO] Found 1 camera(s)
✓✓ Camera connected successfully
```

### Test 3: Run App

```bash
python main.py
```

---

## ❓ FAQ

**Q: Tôi đã có MvCameraControl.dll trong folder rồi mà?**

A: Chỉ có 1 file DLL KHÔNG ĐỦ! Cần toàn bộ Runtime với 40+ DLL.

**Q: Tại sao phải restart máy?**

A: Windows cần restart để load PATH mới. Nếu không restart, PATH cũ vẫn được dùng.

**Q: Tôi không có quyền admin để cài MVS?**

A: Dùng Giải pháp 2 (copy Runtime folder) hoặc Giải pháp 3 (dùng MindVision).

**Q: Có thể chạy offline không?**

A: Có! Dùng Giải pháp 2 - copy Runtime folder vào project.

**Q: MindVision SDK có tốt không?**

A: Có! MindVision SDK đang hoạt động tốt. MVS SDK chỉ là option thêm.

---

## 📋 Checklist Fix

Sau khi làm theo 1 trong 3 giải pháp:

- [ ] `python check_mvs_dependencies.py` → All ✓
- [ ] `where.exe MvCameraControl.dll` → Returns valid path
- [ ] `python test_mvs_camera.py` → Connection OK
- [ ] `python main.py` → App chạy OK

---

## 🆘 Vẫn Không Work?

Check file chi tiết: [docs/MVS-DLL-Problem-Solution.md](docs/MVS-DLL-Problem-Solution.md)

Hoặc:

1. Post log từ: `python check_mvs_dependencies.py`
2. Screenshot lỗi
3. Cho biết đã làm giải pháp nào (1, 2, hay 3)

---

## 🎯 TL;DR

```bash
# Fix nhanh nhất:
1. Cài MVS SDK từ Hikvision
2. Thêm PATH: C:\Program Files\MVS\Runtime\Win64_x64
3. RESTART MÁY
4. python check_mvs_dependencies.py
5. python test_mvs_camera.py
6. python main.py

# Hoặc đơn giản:
# Đổi camera_type: "mindvision" trong camera.yaml
```

---

**Good luck!** 🚀
