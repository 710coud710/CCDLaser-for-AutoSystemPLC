Dưới đây là nội dung file **`huong_dan_mo_camera_python.md`** bắt đầu từ **Bước 2**, đã format chuẩn Markdown để bạn lưu thành file `.md`.

---

# HƯỚNG DẪN MỞ CAMERA GigE BẰNG PYTHON (MVS SDK)

---

## ✅ BƯỚC 2: Chuẩn bị thư viện Python của MVS

Sau khi cài đặt MVS thành công, vào thư mục:

```
C:\Program Files\MVS\Development\Samples\Python\MvImport
```

Copy các file sau vào thư mục project Python của bạn:

```
MvCameraControl_class.py
CameraParams_header.py
MvErrorDefine_const.py
PixelType_header.py
```

> ⚠ Không được thiếu file, nếu thiếu sẽ lỗi import.

---

## ✅ BƯỚC 3: Kiểm tra Python 64-bit

MVS Runtime là 64-bit, vì vậy Python cũng phải là 64-bit.

Kiểm tra bằng cách:

```bash
python
>>> import platform
>>> platform.architecture()
```

Kết quả phải là:

```
('64bit', ...)
```

Nếu là 32bit → cần cài lại Python 64bit.

---

## ✅ BƯỚC 4: Thêm PATH cho MVS Runtime

Vào:

```
Control Panel → System → Advanced system settings
→ Environment Variables → Path
```

Thêm đường dẫn:

```
C:\Program Files\MVS\Runtime\Win64_x64
```

Hoặc:

```
C:\Program Files\MVS\Runtime\Win64
```

Sau đó **restart máy**.

> Nếu không thêm PATH sẽ lỗi: `DLL load failed`

---

## ✅ BƯỚC 5: Cài thư viện Python cần thiết

```bash
pip install numpy opencv-python
```

---

## ✅ BƯỚC 6: Code Python mở camera GigE (phiên bản ổn định)

File ví dụ: `open_camera.py`

```python
import sys
import numpy as np
import cv2
from ctypes import *
from MvCameraControl_class import *

def main():

    deviceList = MV_CC_DEVICE_INFO_LIST()
    tlayerType = MV_GIGE_DEVICE

    # 1. Tìm camera
    ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
    if ret != 0 or deviceList.nDeviceNum == 0:
        print("Không tìm thấy camera!")
        return

    print("Tìm thấy", deviceList.nDeviceNum, "camera")

    # 2. Tạo camera object
    cam = MvCamera()
    stDeviceList = cast(deviceList.pDeviceInfo[0],
                        POINTER(MV_CC_DEVICE_INFO)).contents

    # 3. Tạo handle
    ret = cam.MV_CC_CreateHandle(stDeviceList)
    if ret != 0:
        print("Create handle fail")
        return

    # 4. Mở camera
    ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
    if ret != 0:
        print("Open device fail")
        return

    print("Camera opened")

    # 5. Tối ưu Packet Size cho GigE
    packetSize = cam.MV_CC_GetOptimalPacketSize()
    if int(packetSize) > 0:
        cam.MV_CC_SetIntValue("GevSCPSPacketSize", packetSize)

    # 6. Tắt Trigger Mode (Free run)
    cam.MV_CC_SetEnumValue("TriggerMode", 0)

    # 7. Start Grabbing
    cam.MV_CC_StartGrabbing()

    stOutFrame = MV_FRAME_OUT()

    while True:
        ret = cam.MV_CC_GetImageBuffer(stOutFrame, 1000)

        if ret == 0:
            pData = cast(
                stOutFrame.pBufAddr,
                POINTER(c_ubyte * stOutFrame.stFrameInfo.nFrameLen)
            ).contents

            img = np.frombuffer(pData, dtype=np.uint8)

            height = stOutFrame.stFrameInfo.nHeight
            width = stOutFrame.stFrameInfo.nWidth

            img = img.reshape((height, width))

            cv2.imshow("Camera", img)

            cam.MV_CC_FreeImageBuffer(stOutFrame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cam.MV_CC_StopGrabbing()
    cam.MV_CC_CloseDevice()
    cam.MV_CC_DestroyHandle()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

---

## ▶ Chạy chương trình

```bash
python open_camera.py
```

Nếu thành công:

* Cửa sổ hiển thị hình ảnh
* Nhấn `ESC` để thoát

---

## 📌 Nếu camera là Color (Bayer)

Thêm dòng convert trước khi `imshow`:

```python
img = cv2.cvtColor(img, cv2.COLOR_BAYER_RG2BGR)
```

---

## 🚨 Xử lý lỗi thường gặp

### Không tìm thấy camera

* Kiểm tra ping IP camera
* Tắt firewall
* Đảm bảo cùng lớp mạng

### DLL load failed

* Chưa thêm PATH Runtime
* Python sai phiên bản 32-bit

### Mất frame / giật hình

* Bật Jumbo Frame = 9000
* Dùng dây LAN tốt
* Không dùng chung mạng công ty

---

## 🎯 Kết quả mong muốn

✔ Python detect được camera
✔ Open thành công
✔ Hiển thị hình realtime
✔ ESC để thoát an toàn

---

Nếu cần phiên bản:

* Trigger mode
* Set Exposure / Gain
* Set ROI
* Lưu ảnh
* Tối ưu cho camera 20MP (5488×3672)

Bạn có thể mở rộng thêm vào file này.
