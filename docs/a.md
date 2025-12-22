Dưới đây là **nội dung đã được viết lại gọn – đủ – đúng kỹ thuật**, ở dạng **Markdown chuẩn (.md)** để bạn **đưa thẳng vào file**.

---

```md
# Camera Specification – MindVision Industrial Camera

## 1. Purpose

Tài liệu này mô tả **công nghệ sử dụng**, **phương thức kết nối** và **nguyên tắc điều khiển** đối với **camera công nghiệp MindVision** trong hệ thống vision, phục vụ các tác vụ:

- Chụp ảnh công nghiệp
- Đọc QR / Serial Number
- Xử lý ảnh
- Ứng dụng chạy ổn định, lâu dài

Tài liệu mang tính **spec kỹ thuật**, không bao gồm code chi tiết.

---

## 2. Scope

- Camera công nghiệp **MindVision**
- Giao tiếp **GigE Vision**
- Ứng dụng viết bằng **Python**
- Kiến trúc **MVP (Model – View – Presenter)**
- Không phụ thuộc PLC

---

## 3. Technology Stack

### 3.1 Camera SDK
- **MindVision MVS / MV-SDK**
- SDK chính hãng
- Python sử dụng thông qua **Python wrapper đi kèm SDK**

> Không sử dụng OpenCV để mở camera trực tiếp

### 3.2 Software
- Python 3.x
- NumPy (biểu diễn ảnh)
- OpenCV (xử lý ảnh)
- Python logging

---

## 4. Design Principles

### 4.1 Camera là tài nguyên độc quyền
- Mỗi camera chỉ được mở **1 lần**
- Chỉ tồn tại trong **1 process**
- Không cho phép nhiều module mở camera song song

### 4.2 Tách biệt camera khỏi UI và logic nghiệp vụ
- SDK camera chỉ được sử dụng trong **Camera Service**
- Presenter và View không thao tác trực tiếp SDK

---

## 5. Camera Connection Method

### 5.1 Physical Connection
- Gigabit Ethernet (GigE)
- Camera có IP tĩnh, ví dụ:
  - 192.168.1.41
  - 192.168.1.42

---

### 5.2 Connection Flow (BẮT BUỘC)

```

Enumerate Device
→ Create Handle
→ Open Device
→ Set Parameters
→ Start Grabbing
→ Trigger (optional)
→ Get Frame
→ Release Frame
→ Stop Grabbing
→ Close Device
→ Destroy Handle

```md

Sai thứ tự có thể gây treo camera hoặc không reconnect được.

---

### 5.3 Enumerate Device
- Quét camera MindVision trong mạng
- Lọc theo IP hoặc Serial Number
- Xác định đúng camera cần sử dụng

---

### 5.4 Create Handle
- Tạo handle đại diện camera
- Chưa chiếm quyền camera

---

### 5.5 Open Device
- Camera bị lock độc quyền
- Tool khác (MVS Viewer, app khác) không thể truy cập

---

## 6. Camera Configuration

### 6.1 Thời điểm cấu hình
- Cấu hình ngay sau `OpenDevice`
- Chỉ cấu hình **một lần**
- Không cấu hình trong vòng lặp chụp ảnh

### 6.2 Tham số khuyến nghị (QR / SN)

- TriggerMode: OFF (test) / ON (production)
- ExposureAuto: OFF
- ExposureTime: Manual
- GainAuto: OFF
- PixelFormat: Mono8
- FrameRate: Fixed

---

## 7. Image Acquisition Modes

### 7.1 Free-run Mode
- TriggerMode = OFF
- Dùng để test, căn chỉnh camera

### 7.2 Software Trigger Mode
- TriggerMode = ON
- Mỗi trigger → 1 frame
- Dùng cho vận hành chính thức

---

## 8. Frame Handling & Memory Management

### 8.1 Get Frame
- SDK trả raw buffer + thông tin ảnh
- Convert raw buffer → NumPy array
- Ảnh được xử lý bằng OpenCV

### 8.2 Release Frame (BẮT BUỘC)
- Mỗi frame phải được release
- Không release sẽ gây:
  - Memory leak
  - Treo camera sau một thời gian

---

## 9. Multi-Camera Handling

- Mỗi camera:
  - Một CameraService riêng
  - Một handle riêng
- Không share handle giữa các camera

Ví dụ:
- Cam1 → 192.168.1.41
- Cam2 → 192.168.1.42

---

## 10. Threading & Stability

- Camera chạy trong **worker thread**
- UI thread không gọi SDK camera
- CameraService cần:
  - Timeout khi chờ frame
  - Auto close & reopen khi mất kết nối

---

## 11. MVP Architecture Placement

```

Model
└─ CameraService (MindVision SDK)
Presenter
└─ Điều phối luồng xử lý
View
└─ Hiển thị

```md

Presenter không phụ thuộc hãng camera.

---

## 12. Common Issues & Prevention

| Issue | Cause |
|-----|------|
| Device Busy | Camera đang bị tool khác mở |
| Camera freeze | Không release frame |
| QR không ổn định | Auto exposure |
| Không reconnect | Close không đúng thứ tự |

---

## 13. Conclusion

Camera MindVision phải được quản lý như **tài nguyên độc quyền**, kết nối đúng chuỗi SDK và tách biệt hoàn toàn khỏi UI và logic nghiệp vụ.

Thiết kế đúng ngay từ đầu giúp hệ thống:
- Ổn định
- Dễ bảo trì
- Dễ mở rộng
```
