# QR Code Detection Guide

## Tổng quan

Hệ thống QR Detection cho phép bạn:
- Quét mã QR trong nhiều vùng ROI (Region of Interest) khác nhau
- Tự động thử nhiều phương pháp tiền xử lý ảnh để cải thiện tỷ lệ nhận diện
- Customize validation rules cho QR code
- Hiển thị kết quả real-time trên giao diện

## Cấu trúc Module

```
app/model/qr/
├── __init__.py                  # Export classes
├── qr_processor.py              # Tiền xử lý ảnh
└── qr_detection_service.py      # QR detection service
```

## Cấu hình (qr.yaml)

### 1. Enable/Disable QR Detection

```yaml
qr:
  enabled: true  # Bật/tắt QR detection
```

### 2. Cấu hình ROI Regions

Bạn có thể định nghĩa nhiều vùng ROI để quét QR code:

```yaml
roi_regions:
  - name: "QR1"
    enabled: true
    x: 100          # Tọa độ X (pixels hoặc %)
    y: 100          # Tọa độ Y
    width: 300      # Chiều rộng
    height: 300     # Chiều cao
    use_percentage: false  # false = pixels, true = percentage
    
  - name: "QR2"
    enabled: true
    x: 0.5          # 50% chiều rộng ảnh
    y: 0.2          # 20% chiều cao ảnh
    width: 0.3      # 30% chiều rộng
    height: 0.3     # 30% chiều cao
    use_percentage: true
```

**Lưu ý:**
- Khi `use_percentage: true`, các giá trị x, y, width, height nằm trong khoảng 0.0 - 1.0
- Khi `use_percentage: false`, các giá trị là pixels tuyệt đối

### 3. Detection Settings

```yaml
detection:
  max_attempts: 3  # Số lần thử tối đa với các preprocessing khác nhau
  
  preprocessing:
    # Attempt 1: Không xử lý
    - method: "none"
    
    # Attempt 2: Adaptive thresholding (tốt cho ảnh có độ sáng không đều)
    - method: "adaptive_threshold"
      block_size: 11  # Kích thước block (phải là số lẻ)
      c: 2            # Constant trừ đi
    
    # Attempt 3: Histogram equalization (cải thiện contrast)
    - method: "histogram_equalization"
    
    # Attempt 4: Sharpen (làm sắc nét ảnh)
    - method: "sharpen"
      kernel_size: 3
    
    # Attempt 5: Denoise (giảm nhiễu)
    - method: "denoise"
      h: 10  # Filter strength
```

**Các preprocessing methods:**
- `none`: Không xử lý, dùng ảnh gốc
- `adaptive_threshold`: Chuyển sang ảnh đen trắng với ngưỡng thích ứng
- `histogram_equalization`: Cân bằng histogram để tăng contrast
- `sharpen`: Làm sắc nét ảnh
- `denoise`: Giảm nhiễu

### 4. Validation Settings

```yaml
validation:
  min_length: 1           # Độ dài tối thiểu của QR data
  max_length: 0           # Độ dài tối đa (0 = không giới hạn)
  pattern: ""             # Regex pattern (empty = không validate)
  required_prefix: ""     # Tiền tố bắt buộc
  required_suffix: ""     # Hậu tố bắt buộc
```

**Ví dụ validation:**

```yaml
# Chỉ chấp nhận QR code bắt đầu bằng "SN-" và có độ dài 10-20 ký tự
validation:
  min_length: 10
  max_length: 20
  required_prefix: "SN-"
  
# Chỉ chấp nhận QR code có format số
validation:
  pattern: "^[0-9]+$"
```

### 5. Visualization Settings

```yaml
visualization:
  # Vẽ ROI rectangles
  draw_roi: true
  roi_color: [0, 255, 0]      # Green (BGR format)
  roi_thickness: 2
  
  # Vẽ QR codes detected
  draw_qr: true
  qr_color: [255, 0, 0]       # Blue (BGR)
  qr_thickness: 2
  
  # Vẽ QR data text
  draw_text: true
  text_color: [0, 255, 255]   # Yellow (BGR)
  text_size: 0.6
  text_thickness: 2
```

### 6. Logging Settings

```yaml
logging:
  log_results: true           # Log kết quả detection
  log_failures: false         # Log các lần thất bại
  save_debug_images: false    # Lưu ảnh debug
  debug_image_path: "logs/qr_debug"
```

## Sử dụng trong Code

### 1. Khởi tạo QR Detection Service

```python
from app.model.qr import QRDetectionService

# Load config từ YAML
qr_config = settings.get('qr', {})
qr_service = QRDetectionService(qr_config)
```

### 2. Detect QR Codes

```python
import cv2

# Capture frame từ camera
frame = camera.capture_frame()

# Detect QR codes
results = qr_service.detect_qr_codes(frame)

# Xử lý kết quả
for result in results:
    print(f"ROI: {result.roi_name}")
    print(f"Data: {result.data}")
    print(f"Method: {result.preprocessing_method}")
    print(f"Attempt: {result.attempt}")
```

### 3. Draw Results

```python
# Vẽ ROI và QR detection results lên ảnh
output_image = qr_service.draw_results(frame, results)

# Hiển thị
cv2.imshow("QR Detection", output_image)
```

### 4. Update ROI Region Runtime

```python
# Cập nhật tọa độ ROI region
qr_service.update_roi_region(
    roi_name="QR1",
    x=150,
    y=150,
    width=400,
    height=400,
    use_percentage=False
)

# Enable/disable ROI region
qr_service.enable_roi_region("QR2", enabled=False)
```

## Sử dụng trong UI

### 1. Enable QR Detection

1. Kết nối camera và start streaming
2. Check vào checkbox **"Enable QR Detection"**
3. Check vào **"Show ROI Regions"** để hiển thị vùng ROI trên ảnh

### 2. Xem Kết quả

Kết quả QR detection sẽ hiển thị trong text box **"QR Results"**:

```
[QR1] ABC123456789
  Method: adaptive_threshold, Attempt: 1

[QR2] XYZ987654321
  Method: none, Attempt: 0
```

### 3. Clear Results

Click nút **"Clear Results"** để xóa kết quả cũ.

## QRDetectionResult Class

```python
@dataclass
class QRDetectionResult:
    success: bool                    # Detection thành công
    data: str                        # QR data
    roi_name: str                    # Tên ROI region
    attempt: int                     # Lần thử thứ mấy (0-based)
    preprocessing_method: str        # Phương pháp preprocessing
    bbox: Tuple[int, int, int, int] # Bounding box (x, y, w, h)
    polygon: List[Tuple[int, int]]  # Polygon points
    confidence: float                # Confidence (0.0 - 1.0)
```

## Best Practices

### 1. Cấu hình ROI Regions

- Đặt ROI region bao quanh vùng có khả năng xuất hiện QR code
- ROI nhỏ hơn → detection nhanh hơn
- Sử dụng `use_percentage: true` khi muốn ROI tự động scale theo kích thước ảnh

### 2. Preprocessing Methods

- **Ảnh sáng đều:** Dùng `none` hoặc `sharpen`
- **Ảnh tối hoặc sáng không đều:** Dùng `adaptive_threshold`
- **Ảnh có contrast thấp:** Dùng `histogram_equalization`
- **Ảnh có nhiễu:** Dùng `denoise`

### 3. Performance

- Giảm `max_attempts` nếu cần tốc độ cao
- Tắt `save_debug_images` trong production
- Tắt các ROI region không dùng

### 4. Validation

- Sử dụng validation để lọc QR codes không hợp lệ
- Dùng `pattern` (regex) cho validation phức tạp
- Dùng `required_prefix`/`required_suffix` cho validation đơn giản

## Troubleshooting

### QR code không được detect

1. **Check ROI region:** Đảm bảo ROI bao phủ QR code
2. **Tăng max_attempts:** Thử nhiều preprocessing methods hơn
3. **Check validation:** Có thể QR bị reject do validation rules
4. **Enable debug logging:** Set `log_failures: true` để xem chi tiết

### Performance chậm

1. **Giảm ROI size:** ROI nhỏ hơn → xử lý nhanh hơn
2. **Giảm max_attempts:** Ít preprocessing methods hơn
3. **Tắt visualization:** Set `draw_roi: false`, `draw_qr: false`

### QR data không đúng

1. **Check validation rules:** Đảm bảo validation không quá strict
2. **Cải thiện chất lượng ảnh:** Tăng exposure time, giảm gain
3. **Thử preprocessing khác:** Thêm/bớt preprocessing methods

## Example Configurations

### Config 1: Single QR, Center of Image

```yaml
roi_regions:
  - name: "Center"
    enabled: true
    x: 0.35
    y: 0.35
    width: 0.3
    height: 0.3
    use_percentage: true

detection:
  max_attempts: 2
  preprocessing:
    - method: "none"
    - method: "adaptive_threshold"
      block_size: 11
      c: 2
```

### Config 2: Multiple QRs, Different Locations

```yaml
roi_regions:
  - name: "Top-Left"
    enabled: true
    x: 50
    y: 50
    width: 200
    height: 200
    use_percentage: false
    
  - name: "Top-Right"
    enabled: true
    x: 850
    y: 50
    width: 200
    height: 200
    use_percentage: false
    
  - name: "Bottom"
    enabled: true
    x: 0.3
    y: 0.7
    width: 0.4
    height: 0.25
    use_percentage: true
```

### Config 3: High-Performance Mode

```yaml
detection:
  max_attempts: 1
  preprocessing:
    - method: "none"

visualization:
  draw_roi: false
  draw_qr: false
  draw_text: false

logging:
  log_results: false
  log_failures: false
  save_debug_images: false
```

## API Reference

### QRDetectionService

#### Methods

- `detect_qr_codes(image: np.ndarray) -> List[QRDetectionResult]`
  - Detect QR codes trong image
  
- `draw_results(image: np.ndarray, results: List[QRDetectionResult]) -> np.ndarray`
  - Vẽ detection results lên ảnh
  
- `update_roi_region(roi_name: str, x: int, y: int, width: int, height: int, use_percentage: bool)`
  - Cập nhật ROI region
  
- `enable_roi_region(roi_name: str, enabled: bool)`
  - Enable/disable ROI region
  
- `get_roi_regions() -> List[ROIRegion]`
  - Lấy danh sách ROI regions

### QRProcessor

#### Methods

- `preprocess_image(image: np.ndarray, method_index: int) -> np.ndarray`
  - Tiền xử lý ảnh theo method
  
- `get_preprocessing_count() -> int`
  - Lấy số lượng preprocessing methods
  
- `get_preprocessing_name(index: int) -> str`
  - Lấy tên preprocessing method







