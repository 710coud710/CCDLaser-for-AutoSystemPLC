
```md
# MindVision Camera – SDK Connection & Access Specification

## 1. Tổng quan

Camera công nghiệp **MindVision GigE** không được kết nối trực tiếp bằng socket hay IP thuần.  
Việc kết nối và truy cập camera được thực hiện **thông qua MindVision SDK (MVCAMSDK)**, SDK này xử lý toàn bộ giao thức **GigE Vision** ở tầng thấp.

Ứng dụng chỉ làm việc với **API SDK**, không giao tiếp trực tiếp với camera qua TCP/UDP.

---

## 2. Kiến trúc kết nối

Luồng kết nối thực tế:

```

[Camera GigE]
↓ (GigE Vision: GVCP / GVSP)
[MindVision Driver]
↓
[MVCAMSDK.dll / MVCAMSDK_X64.dll]
↓
[mvsdk.py (Python wrapper)]
↓
[Application]

```

- Camera truyền dữ liệu ảnh trực tiếp qua Ethernet
- SDK đảm nhiệm:
  - Broadcast tìm camera
  - Khởi tạo kết nối
  - Quản lý buffer ảnh
  - Điều khiển tham số camera

---

## 3. Điều kiện hệ thống

### 3.1 Phần cứng
- Camera MindVision hỗ trợ GigE
- Card mạng Ethernet (khuyến nghị Intel)
- Kết nối cùng subnet với camera

### 3.2 Mạng
- IP camera dạng: `192.168.x.x`
- Subnet Mask: `255.255.255.0`
- Không yêu cầu Gateway

### 3.3 Phần mềm
- MindVision SDK (Windows)
- Driver camera MindVision
- Python + file `mvsdk.py`

---

## 4. SDK và Driver

### 4.1 SDK
- Cung cấp file:
  - `MVCAMSDK.dll` (32bit)
  - `MVCAMSDK_X64.dll` (64bit)
- SDK được load động bằng `ctypes`

### 4.2 Driver
- Driver GigE Vision của MindVision
- Cài đặt **offline** từ bộ SDK
- Sau khi cài, camera sẽ được SDK nhận diện (không cần Windows Camera)

---

## 5. Nguyên lý “Connect” trong SDK

> **MindVision không có hàm connect bằng IP**

Kết nối camera được thực hiện thông qua chuỗi thao tác sau:

1. **Enumerate Device**
   - SDK broadcast GigE Vision
   - Phát hiện camera trong mạng

2. **CameraInit**
   - Mở camera
   - Thiết lập kênh giao tiếp
   - Gán handle camera

3. **Set Parameter**
   - Trigger mode
   - Resolution
   - Pixel format
   - Exposure, gain

4. **Start Acquisition**
   - Camera bắt đầu stream ảnh
   - SDK nhận và quản lý buffer

📌 Nếu `CameraInit` thành công → camera đã được kết nối.

---

## 6. IP camera dùng để làm gì?

- IP **không dùng để connect thủ công**
- IP chỉ dùng để:
  - Định tuyến dữ liệu GigE Vision
  - Phân biệt camera khi enumerate
  - Hiển thị thông tin thiết bị

Ứng dụng **không**:
- Mở socket tới IP camera
- Gửi TCP/UDP trực tiếp
- Ping để xác nhận kết nối

---

## 7. Nhận diện camera trong ứng dụng

Khi enumerate thành công, SDK cung cấp các thông tin:

- Product Series (GigE)
- Product Name
- Friendly Name
- Serial Number
- Sensor Type
- Port Type (NET-1000M-IP)
- Driver Version

Việc đọc được các thông tin này chứng tỏ camera đã sẵn sàng kết nối.

---

## 8. Xác nhận kết nối thành công

Camera được xem là **kết nối thành công** khi:

- `CameraInit` không trả lỗi
- Có thể đọc thông tin camera
- Có thể grab và lưu ảnh thành công

Ví dụ kết quả:
```

Save image successfully. image_size = 5488x3672

```

---

## 9. Lưu ý quan trọng

- Không thể giả lập camera để SDK nhận như thiết bị thật
- Fake camera chỉ dùng để test logic ứng dụng, không test SDK
- Mỗi camera chỉ được mở bởi **một process tại một thời điểm**
- Rút cáp mạng trong lúc grab có thể gây timeout hoặc exception

---

## 10. Phạm vi sử dụng tài liệu

Tài liệu này dùng để:
- Hiểu cơ chế kết nối camera MindVision
- Thiết kế hệ thống capture ảnh
- Debug lỗi kết nối GigE
- Viết ứng dụng automation, vision inspection

---
```

---
