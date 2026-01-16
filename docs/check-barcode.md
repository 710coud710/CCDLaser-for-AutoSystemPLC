# Hướng dẫn CHECK QR / DATAMATRIX bằng CCD (Recipe-based Vision)

Tài liệu này mô tả **toàn bộ quy trình từ con số 0** đến khi hệ thống CCD có thể **tự động check QR / DataMatrix** dựa trên **bản mẫu (recipe) được tạo từ ảnh chụp thực tế**.

Phương pháp áp dụng: **Template Matching + ROI QR (Teaching Mode)**
👉 Không dùng AI, phù hợp môi trường công nghiệp (PCB / SMT / AOI).

---

## 1. Mục tiêu hệ thống

Hệ thống cần đạt được:

* Nhận ảnh trực tiếp từ camera CCD
* Cho phép **tạo bản mẫu (Master / Recipe)** từ panel chuẩn
* Lưu vị trí định vị + vùng QR/DataMatrix vào setting
* Khi panel mới vào:

  * Tự động căn chỉnh theo bản mẫu
  * Tự động chọn đúng vùng QR
  * Decode QR / DataMatrix
  * Trả kết quả OK / NG

---

## 2. Chuẩn bị ban đầu

### 2.1 Phần cứng

* Camera CCD (fixed, không rung)
* Lens phù hợp (QR chiếm ≥ 50–80 px cạnh nhỏ)
* Đèn chiếu sáng ổn định (ring / bar / coaxial)
* Bàn gá hoặc cơ cấu giữ panel ổn định

### 2.2 Phần mềm

* SDK camera (MindVision / Hik / Basler…)
* Thư viện xử lý ảnh (OpenCV hoặc tương đương)
* Thư viện đọc QR / DataMatrix
* Module lưu setting (JSON / DB / file config)

---

## 3. Tổng quan luồng xử lý

```
CAMERA → IMAGE
        ↓
  TEMPLATE MATCHING
        ↓
 OFFSET (dx, dy, angle)
        ↓
 TRANSFORM QR ROI
        ↓
 QR / DATAMATRIX DECODE
        ↓
   CHECK RESULT
```

---

## 4. Bước 1 – Chụp ảnh panel chuẩn (Master Image)

1. Đặt **panel chuẩn (panel tốt)** vào đúng vị trí cơ khí
2. Chụp ảnh từ camera CCD
3. Lưu ảnh này làm **ảnh master**

Yêu cầu:

* Panel không bị nghiêng lệch
* Ánh sáng đúng cấu hình chạy thực tế

---

## 5. Bước 2 – Tạo bản mẫu (Teaching Mode)

### 5.1 Chọn vùng định vị (Template Region)

Người vận hành chọn **1 vùng đặc trưng ổn định** trên panel:

* Fiducial
* Góc PCB
* Mép đồng
* Pattern có độ tương phản cao

Mục đích:

* Dùng vùng này để **so khớp vị trí & góc panel**

Lưu ý:

* Không chọn vùng trống
* Không chọn vùng dễ thay đổi ánh sáng

---

### 5.2 Chọn vùng QR / DataMatrix (QR ROI)

1. Trên **cùng ảnh master**, chọn vùng chứa QR/DataMatrix
2. ROI nên:

   * Rộng hơn QR 10–20%
   * Không cắt sát mép mã

Quan trọng:

* **ROI QR phải được lưu theo tọa độ tương đối với template**, KHÔNG dùng tọa độ tuyệt đối ảnh

---

### 5.3 Thiết lập ngưỡng sai lệch (Tolerance)

Thiết lập các giới hạn cho phép:

* Lệch X (mm hoặc pixel)
* Lệch Y
* Góc xoay (độ)

Ví dụ:

* ΔX ≤ ±0.5 mm
* ΔY ≤ ±0.5 mm
* ΔAngle ≤ ±2°

---

## 6. Bước 3 – Lưu Recipe vào Setting

Mỗi recipe tương ứng **1 loại panel**.

Nội dung cần lưu:

* Ảnh template
* Thông tin template region
* Thông tin QR ROI (relative)
* Pose chuẩn (X, Y, Angle)
* Tolerance
* Tham số decode QR

Recipe được lưu vào:

* File cấu hình
* Hoặc database

---

## 7. Bước 4 – Xử lý khi panel chạy thực tế

### 7.1 Nhận ảnh từ camera

* Chụp ảnh panel mới
* Dùng cùng cấu hình ánh sáng & camera

---

### 7.2 So khớp template (Template Matching)

* Thực hiện match template
* Tính ra:

  * Vị trí panel hiện tại
  * Góc xoay
  * Độ lệch so với master

Nếu sai lệch vượt tolerance → **NG (reject sớm)**

---

### 7.3 Biến đổi ROI QR (ROI Transform)

* Áp dụng offset (dx, dy, angle)
* Dịch & xoay ROI QR theo panel thực tế

Kết quả:

* ROI QR mới nằm đúng vị trí QR trên panel hiện tại

---

### 7.4 Decode QR / DataMatrix

* Crop ảnh theo ROI QR đã transform
* Thực hiện decode
* Kiểm tra:

  * Có đọc được không
  * Nội dung đúng format không

---

## 8. Bước 5 – Check & Trả kết quả

### 8.1 Các trạng thái kết quả

* **OK**: đọc QR thành công + đúng nội dung
* **NG – No code**: không đọc được QR
* **NG – Position**: panel lệch vượt tolerance
* **NG – Format**: QR sai format / sai dữ liệu

---

### 8.2 Gửi kết quả ra ngoài

* Trả tín hiệu cho PLC
* Gửi dữ liệu lên MES / Server
* Lưu log ảnh NG (nếu cần)

---

## 9. Các lỗi thường gặp & cách tránh

### ❌ Lưu ROI QR theo tọa độ ảnh tuyệt đối

→ Panel lệch là đọc sai

✅ Luôn lưu ROI QR **relative với template**

---

### ❌ Template chọn vùng yếu

→ Match không ổn định

✅ Chọn vùng có chi tiết rõ, ít thay đổi

---

### ❌ ROI QR quá nhỏ

→ QR bị cắt khi panel lệch

✅ ROI lớn hơn QR 10–20%

---

## 10. Khi nào cần nâng cấp thêm?

* Nhiều loại panel → Multi-recipe
* QR mờ → kiểm tra chất lượng mã
* QR không cố định → Barcode detection hoặc AI

---

## 11. Kết luận

* Đây là **giải pháp chuẩn công nghiệp**
* Không cần AI
* Ổn định – nhanh – dễ bảo trì
* Phù hợp hệ thống CCD + PLC + PCB

