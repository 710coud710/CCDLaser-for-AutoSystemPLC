# MVS DLL Problem - Giải Pháp Chi Tiết

## 🔴 Vấn Đề

```
FileNotFoundError: Could not find module 'MvCameraControl.dll' 
(or one of its dependencies). Try using the full path with constructor syntax.
```

## ⚠️ Nguyên Nhân

**MvCameraControl.dll KHÔNG THỂ CHẠY ĐỘC LẬP!**

File `MvCameraControl.dll` cần **NHIỀU DLL khác** (dependencies):

```
MvCameraControl.dll
    ├── MVGigEVisionSDK.dll       ← Cần cho GigE camera
    ├── MVUSB3VisionSDK.dll        ← Cần cho USB camera
    ├── MvGenTLProducerSDK.dll     ← GenTL interface
    ├── log4cpp_D.dll              ← Logging
    ├── ImageConvert.dll           ← Image processing
    ├── MediaProcess.dll           ← Media processing
    ├── MvMatchTracking.dll        ← Tracking features
    └── [nhiều DLL khác...]        ← 20+ dependencies!
```

→ **Chỉ copy 1 file MvCameraControl.dll = KHÔNG ĐỦ!**

## ✅ Giải Pháp

### 🎯 Option 1: Cài MVS SDK Đầy Đủ (KHUYÊN DÙNG)

#### Bước 1: Download MVS SDK

1. Truy cập: https://www.hikrobotics.com/en/machinevision/service/download
2. Chọn: **MVS (Machine Vision Software)**
3. Download: **Windows 64-bit version**
4. File: `MVS_xxx_Win64.exe` (khoảng 500MB)

#### Bước 2: Cài Đặt MVS SDK

```
1. Chạy file cài đặt MVS_xxx_Win64.exe
2. Chọn "Typical" installation
3. Installation path: C:\Program Files\MVS\
4. Cài đặt runtime components
5. Hoàn tất cài đặt
```

Sau khi cài, sẽ có folder:
```
C:\Program Files\MVS\
    ├── Runtime\
    │   ├── Win64_x64\           ← DLL folder chính
    │   │   ├── MvCameraControl.dll
    │   │   ├── MVGigEVisionSDK.dll
    │   │   └── [40+ DLL files...]
    │   └── Win64\                ← Alternative location
    └── Development\
        └── Samples\
            └── Python\           ← Python samples
                └── MvImport\     ← Python bindings
```

#### Bước 3: Thêm vào PATH

**Windows:**

```
1. Right-click "This PC" → Properties
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "System variables", select "Path" → Edit
5. Click "New"
6. Add: C:\Program Files\MVS\Runtime\Win64_x64
7. Click OK, OK, OK
8. ⚠️ RESTART MÁY (QUAN TRỌNG!)
```

**PowerShell Admin (Alternative):**

```powershell
# Check current PATH
$env:Path -split ';' | Select-String MVS

# Add to system PATH (requires admin)
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\MVS\Runtime\Win64_x64",
    [EnvironmentVariableTarget]::Machine
)

# Restart required!
```

#### Bước 4: Verify

```bash
# Check PATH
echo $env:PATH | Select-String MVS

# Check DLL
where.exe MvCameraControl.dll

# Run checker
python check_mvs_dependencies.py
```

Expected output:
```
✓ Python 64-bit OK
✓ Found MVS Runtime: C:\Program Files\MVS\Runtime\Win64_x64
✓ MVS Runtime is in PATH
✓ Import SUCCESS!
✓✓✓ ALL CHECKS PASSED!
```

---

### 🔧 Option 2: Copy Toàn Bộ Runtime (Portable)

Nếu không thể cài MVS (không có quyền admin, offline...):

#### Bước 1: Lấy MVS Runtime từ máy khác

Từ máy đã cài MVS, copy toàn bộ folder:
```
C:\Program Files\MVS\Runtime\Win64_x64\
```

#### Bước 2: Paste vào Project

```
D:\Beta\CCDLaser\
    └── mvs_runtime\           ← Tạo folder mới
        ├── MvCameraControl.dll
        ├── MVGigEVisionSDK.dll
        └── [tất cả DLL...]    ← Copy ALL files!
```

**Quan trọng:** Phải copy **TẤT CẢ** files trong folder Win64_x64!

#### Bước 3: Code sẽ tự động tìm

Script `mvs_camera.py` đã được update để tự động tìm DLL trong:
- Project root
- `mvs_runtime/` folder
- System PATH

```python
# mvs_camera.py tự động add paths:
dll_search_paths = [
    project_root,
    project_root + "/mvs_runtime",
    "C:/Program Files/MVS/Runtime/Win64_x64",
]
```

---

### 🔄 Option 3: Fallback - Dùng MindVision SDK

Nếu không thể sử dụng MVS SDK:

#### Bước 1: Sửa Config

```yaml
# setting/camera.yaml
camera:
  camera_type: "mindvision"  # ← Chuyển về MindVision
  ip: "0"
```

#### Bước 2: Restart App

```bash
python main.py
```

MindVision SDK (mvsdk.py) không có vấn đề DLL dependencies phức tạp.

---

## 🔍 Troubleshooting

### Test 1: Check Dependencies

```bash
python check_mvs_dependencies.py
```

Script này sẽ check:
- ✓ Python 64-bit
- ✓ MVS Runtime location
- ✓ DLL files
- ✓ PATH environment
- ✓ Import test

### Test 2: Manual DLL Check

```bash
# Check if DLL exists
where.exe MvCameraControl.dll

# Check dependencies (requires Dependency Walker)
# Download: http://www.dependencywalker.com/
depends.exe MvCameraControl.dll
```

### Test 3: Python Test

```python
import sys
import os

# Add DLL path
dll_path = r"C:\Program Files\MVS\Runtime\Win64_x64"
os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']

# Try import
from MvCameraControl_class import MvCamera
print("Import OK!")
```

---

## 📋 Common Errors

### Error 1: "DLL load failed"

```
FileNotFoundError: Could not find module 'MvCameraControl.dll'
```

**Cause:** DLL not in PATH or missing dependencies

**Fix:**
1. Add MVS Runtime to PATH
2. Restart machine
3. Verify: `where.exe MvCameraControl.dll`

### Error 2: "ImportError: DLL load failed while importing"

```
ImportError: DLL load failed while importing MvCameraControl_class
```

**Cause:** Missing dependency DLLs (MVGigEVisionSDK.dll, etc.)

**Fix:**
1. Install full MVS SDK (Option 1)
2. Or copy ALL DLLs from Runtime folder (Option 2)

### Error 3: "Python 32-bit"

```
ERROR: MVS SDK requires Python 64-bit!
```

**Fix:**
1. Uninstall Python 32-bit
2. Install Python 64-bit from python.org
3. Recreate venv

---

## 🎯 Quick Fix Checklist

- [ ] Python 64-bit installed?
- [ ] MVS SDK installed?
- [ ] Runtime folder exists: `C:\Program Files\MVS\Runtime\Win64_x64\`
- [ ] PATH contains Runtime folder?
- [ ] Machine restarted after PATH change?
- [ ] `where.exe MvCameraControl.dll` returns valid path?
- [ ] `python check_mvs_dependencies.py` passes all checks?

---

## 🚀 After Fix

Sau khi fix xong:

```bash
# 1. Verify dependencies
python check_mvs_dependencies.py

# 2. Test MVS connection
python test_mvs_camera.py

# 3. Run main app
python main.py
```

Expected:
```
[INFO] Creating MVS camera instance...
[INFO] MVS SDK loaded successfully
[INFO] Enumerating devices...
[INFO] Found 1 camera(s)
✓✓ Camera connected successfully
```

---

## 📚 References

- **MVS SDK Download:** https://www.hikrobotics.com/en/machinevision/service/download
- **MVS User Manual:** Included in SDK installation
- **Python Samples:** `C:\Program Files\MVS\Development\Samples\Python\`
- **Dependency Walker:** http://www.dependencywalker.com/

---

## 💡 Key Takeaways

1. **MvCameraControl.dll ≠ Standalone**
   - Cần 40+ DLL dependencies
   - Phải có toàn bộ Runtime folder

2. **PATH is Critical**
   - Windows phải biết nơi tìm DLL
   - Restart máy sau khi thêm PATH

3. **64-bit Only**
   - MVS SDK chỉ hỗ trợ 64-bit
   - Python phải là 64-bit

4. **Portable Option Works**
   - Có thể copy Runtime folder vào project
   - Không cần install nếu copy đủ files

5. **MindVision is Fallback**
   - Nếu MVS không work → dùng MindVision
   - Đổi config là xong

---

**Summary:** Chỉ có `MvCameraControl.dll` KHÔNG ĐỦ! Cần cài MVS SDK đầy đủ hoặc copy toàn bộ Runtime folder.
