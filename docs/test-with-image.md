# Hướng dẫn Test QR Code với Ảnh (Không cần Camera)

## Tổng quan

Tính năng này cho phép bạn test QR code detection với ảnh từ file, không cần kết nối camera thực. Rất hữu ích cho:
- Debug và phát triển
- Test với nhiều ảnh mẫu khác nhau
- Kiểm tra recipe trước khi deploy

## Các bước thực hiện

### 1. Chuẩn bị Recipe

Trước tiên, bạn cần có một recipe đã được tạo sẵn:

**Cách 1: Sử dụng recipe có sẵn**
- Vào tab "Running Mode"
- Chọn recipe từ dropdown list
- Click "Load Recipe"

**Cách 2: Tạo recipe mới (nếu chưa có)**
- Vào tab "Teaching Mode"
- Click "Load Image from File" để load ảnh master
- Click "Select Template Region" và chọn vùng template trên ảnh
- Click "Add QR ROI" để thêm các vùng QR cần detect
- Nhập tên recipe và click "Save Recipe"

### 2. Load Ảnh Test

Trong tab "Running Mode":

1. Tìm section **"Test Image Source"**
2. Click nút **"Load Image for Testing"**
3. Chọn file ảnh cần test (hỗ trợ: .png, .jpg, .jpeg, .bmp)
4. Ảnh sẽ được hiển thị trên màn hình

### 3. Xử lý Ảnh Test

1. Đảm bảo đã load recipe (bước 1)
2. Click nút **"Process Test Image"**
3. Hệ thống sẽ:
   - Thực hiện template matching để tìm vị trí panel
   - Kiểm tra tolerance (độ lệch vị trí)
   - Detect QR code trong các ROI đã định nghĩa
   - Hiển thị kết quả trên ảnh và trong log

### 4. Xem Kết quả

**Trên ảnh:**
- Vùng template match (nếu bật "Show Template Match")
- Vùng ROI và QR code detected (nếu bật "Show ROI Regions")

**Trong log "QR Results":**
- `[OK]` - QR code detected thành công
- `[NG]` - Không detect được hoặc vị trí sai
- Thông tin: ROI name, data, preprocessing method, attempt number

## Ví dụ

### Test với ảnh có sẵn

```
Ảnh test có sẵn trong project:
- test/PT524R0655120CGJ.JPEG
- recipes_test/images/Test_Recipe_20260107_133420.png
- recipes_test/images/Test_Recipe_20260107_133434.png
```

### Workflow điển hình

1. **Load recipe "Test_Recipe"**
   - Tab "Running Mode" → Select "Test_Recipe" → "Load Recipe"

2. **Load ảnh test**
   - "Load Image for Testing" → Chọn `recipes_test/images/Test_Recipe_20260107_133420.png`

3. **Process**
   - "Process Test Image"

4. **Kiểm tra kết quả**
   - Xem ảnh có vẽ ROI và QR code không
   - Đọc log trong "QR Results"

## Lưu ý

- **Recipe phải match với ảnh**: Recipe được tạo từ ảnh master phải tương tự với ảnh test (cùng loại panel, vị trí tương đối)
- **Template matching**: Nếu template matching fail, QR detection sẽ không chạy
- **Tolerance**: Nếu vị trí panel lệch quá tolerance, sẽ báo NG
- **Multiple attempts**: Hệ thống tự động thử nhiều preprocessing method để tăng tỷ lệ detect

## So sánh với Camera Mode

| Tính năng | Camera Mode | Image Test Mode |
|-----------|-------------|-----------------|
| Nguồn ảnh | Camera thực | File ảnh |
| Streaming | Liên tục | Xử lý 1 lần |
| Kết nối | Cần camera | Không cần |
| Use case | Production | Development/Debug |

## Troubleshooting

**Không detect được QR code:**
- Kiểm tra recipe có đúng không
- Kiểm tra ROI có bao phủ QR code không
- Thử với ảnh có độ phân giải tốt hơn
- Kiểm tra QR code có rõ ràng không

**Template matching fail:**
- Ảnh test khác quá nhiều so với master image
- Thử tăng search_margin trong code
- Thử giảm min_match_score trong recipe

**Vị trí panel NG:**
- Điều chỉnh tolerance trong recipe
- Kiểm tra ảnh có bị xoay/lệch nhiều không

## Tích hợp với Workflow

Tính năng này có thể dùng để:
1. **Validate recipe** trước khi dùng trong production
2. **Debug** khi có lỗi trong production (chụp ảnh, đem về test)
3. **Training** nhân viên mới
4. **Demo** cho khách hàng mà không cần setup camera

---

*Cập nhật: 2026-01-15*

