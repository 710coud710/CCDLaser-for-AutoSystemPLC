Dưới đây là **nội dung hoàn chỉnh của file `camera-spec.md`**
→ viết theo **đúng kiểu tài liệu kỹ thuật (spec)** để bạn **dựng base, maintain lâu dài**, phù hợp **Python + MVP + camera công nghiệp MindVision**.

Bạn có thể **copy nguyên file này** đưa vào project.

---

# camera-spec.md

## 1. Mục đích tài liệu

Tài liệu này mô tả **công nghệ sử dụng**, **phương thức kết nối**, và **nguyên tắc điều khiển** đối với **camera công nghiệp MindVision** trong hệ thống thị giác máy (Vision System), phục vụ cho các bài toán:

* Chụp ảnh công nghiệp
* Đọc QR / SN
* Xử lý ảnh
* Ứng dụng chạy lâu dài, ổn định

Tài liệu này **không chứa code**, chỉ mô tả **kiến trúc và logic điều khiển**.

---

## 2. Phạm vi áp dụng

* Camera công nghiệp **MindVision**
* Giao tiếp **GigE Vision**
* Ứng dụng viết bằng **Python**
* Kiến trúc **MVP (Model – View – Presenter)**
* Không phụ thuộc PLC

---

## 3. Công nghệ sử dụng

### 3.1 Camera SDK

* **MindVision MVS / MV-SDK**
* SDK chính hãng do MindVision cung cấp
* Hỗ trợ:

  * GigE camera
  * USB camera
* Python sử dụng thông qua:

  * Python wrapper chính hãng đi kèm SDK

> ⚠️ Không sử dụng OpenCV để mở camera trực tiếp

---

### 3.2 Ngôn ngữ & thư viện

* Python 3.x
* OpenCV (cv2) – chỉ dùng cho xử lý ảnh
* NumPy – biểu diễn ảnh
* Logging (python logging)

---

## 4. Nguyên tắc thiết kế (Design Principles)

### 4.1 Tách biệt phần camera

* Camera **chỉ được điều khiển tại một module duy nhất**
* Không cho phép:

  * View mở camera
  * Presenter thao tác SDK trực tiếp

Camera được coi là **tài nguyên độc quyền (exclusive resource)**.

---

### 4.2 Một camera – một handle – một process

* Mỗi camera MindVision:

  * Chỉ được `OpenDevice` **1 lần**
  * Chỉ tồn tại trong **1 process**
* Mở camera ở nhiều nơi sẽ gây lỗi **Device Busy**

---

## 5. Phương thức kết nối camera MindVision

### 5.1 Kiểu kết nối vật lý

* Gigabit Ethernet (GigE)
* Camera có địa chỉ IP tĩnh, ví dụ:

  * 192.168.1.41
  * 192.168.1.42

---

### 5.2 Chuỗi kết nối logic (Connection Flow)

Chuỗi kết nối **bắt buộc tuân thủ đúng thứ tự**:

```
Enumerate Device
→ Create Handle
→ Open Device
→ Set Camera Parameters
→ Start Grabbing
→ Trigger (optional)
→ Get Frame
→ Release Frame
→ Stop Grabbing
→ Close Device
→ Destroy Handle
```

Sai thứ tự có thể gây:

* Treo camera
* Không reconnect được
* Phải reboot camera

---

### 5.3 Enumerate Device

* SDK quét toàn bộ camera MindVision trong mạng
* Lọc camera theo:

  * IP
  * Serial Number
* Chỉ định rõ camera cần kết nối

---

### 5.4 Create Handle

* Tạo handle đại diện cho camera
* Chưa chiếm quyền camera ở bước này

---

### 5.5 Open Device

* Camera bị lock độc quyền
* Không cho phép:

  * Tool MVS Viewer
  * Ứng dụng khác
    truy cập đồng thời

---

## 6. Cấu hình camera (Camera Configuration)

### 6.1 Thời điểm cấu hình

* Cấu hình **ngay sau khi OpenDevice**
* Chỉ cấu hình **một lần**
* Không cấu hình trong vòng lặp chụp ảnh

---

### 6.2 Tham số khuyến nghị (QR / SN)

* TriggerMode: OFF (test) / ON (production)
* ExposureAuto: OFF
* ExposureTime: Manual
* GainAuto: OFF
* PixelFormat: Mono8
* FrameRate: cố định

---

## 7. Phương thức chụp ảnh

### 7.1 Free-run (test, debug)

* TriggerMode = OFF
* Camera stream liên tục
* Dùng để:

  * Căn chỉnh camera
  * Test chất lượng ảnh

---

### 7.2 Software Trigger (production)

* TriggerMode = ON
* Mỗi lần chụp:

  * App gửi lệnh trigger
  * Camera trả về đúng 1 frame

---

## 8. Lấy ảnh và quản lý bộ nhớ

### 8.1 Get Frame

* SDK trả về:

  * Raw buffer
  * Thông tin width, height, pixel format
* Raw buffer được convert sang:

  * NumPy array
  * Sau đó xử lý bằng OpenCV

---

### 8.2 Release Frame (BẮT BUỘC)

* Mỗi frame lấy ra **phải được release**
* Không release frame sẽ:

  * Gây memory leak
  * Treo camera sau thời gian ngắn

---

## 9. Xử lý đa camera

* Mỗi camera:

  * Một instance CameraService
  * Một handle độc lập
* Không share handle giữa các camera

Ví dụ:

* Cam1 → 192.168.1.41
* Cam2 → 192.168.1.42

---

## 10. Threading & Stability

### 10.1 Nguyên tắc

* Camera chạy trong **worker thread**
* UI thread **không được** gọi SDK camera

---

### 10.2 Timeout & Reconnect

Camera service cần:

* Timeout khi chờ frame
* Auto:

  * Stop
  * Close
  * Re-open camera khi mất kết nối

---

## 11. Vị trí camera trong kiến trúc MVP

```
Model
└─ CameraService
   └─ MindVision SDK
Presenter
└─ Điều phối luồng
View
└─ Hiển thị kết quả
```

Presenter **không biết camera là MindVision hay hãng khác**.

---

## 12. Các lỗi thường gặp & phòng tránh

| Lỗi              | Nguyên nhân                 |
| ---------------- | --------------------------- |
| Device Busy      | Camera đang bị tool khác mở |
| Treo camera      | Không release frame         |
| QR không ổn định | Auto exposure               |
| Không reconnect  | Không close đúng thứ tự     |

---

## 13. Kết luận

Camera MindVision trong hệ thống vision công nghiệp **phải được coi là tài nguyên độc quyền**, được quản lý tập trung, kết nối theo đúng chuỗi SDK, và tách biệt hoàn toàn khỏi UI và logic nghiệp vụ.

Thiết kế đúng ngay từ đầu giúp:

* Ứng dụng ổn định
* Dễ bảo trì
* Dễ mở rộng sang camera khác trong tương lai

---

Nếu bạn muốn, bước tiếp theo mình có thể giúp bạn viết tiếp:

* `lighting-spec.md`
* `vision-flow-spec.md`
* `camera-state-machine.md`
* hoặc review lại **spec tổng thể của project**

👉 Chỉ cần nói **tiếp file nào**.
