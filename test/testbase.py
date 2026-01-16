import cv2
import numpy as np
import requests
from pylibdmtx.pylibdmtx import decode
import matplotlib.pyplot as plt
import os
def load_image(src):
    # Case 1: URL
    if src.startswith("http://") or src.startswith("https://"):
        resp = requests.get(src, timeout=10)
        img_arr = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        return img

    # Case 2: Local file
    if os.path.exists(src):
        return cv2.imread(src)

    raise ValueError(f"Invalid image source: {src}")

def load_image_from_url(url):
    resp = requests.get(url)
    img_arr = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    return img


def show(img, title):
    plt.figure(figsize=(4,4))
    if len(img.shape) == 2:
        plt.imshow(img, cmap="gray")
    else:
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.title(title)
    plt.axis("off")
    plt.show()


# ===============================
# MAIN
# ===============================
image_url = r"D:/Beta/CCDLaser/test/check.JPEG"

img = load_image(image_url)
show(img, "1. Original Image")

# 1️⃣ Grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
show(gray, "2. Grayscale")

# 2️⃣ Tăng tương phản (CLAHE)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
contrast = clahe.apply(gray)
show(contrast, "3. CLAHE - Contrast Enhanced")

# 3️⃣ Giảm nhiễu
denoise = cv2.medianBlur(contrast, 3)
show(denoise, "4. Median Blur (Denoise)")

# 4️⃣ Nhị phân hóa
binary = cv2.adaptiveThreshold(
    denoise,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    31,
    5
)
show(binary, "5. Adaptive Threshold")

# 5️⃣ Morphology
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
show(morph, "6. Morphology Close")

# ===============================
# Decode DataMatrix
# ===============================
print("🔍 Decoding DataMatrix...")

decoded = []
for src, name in [
    (gray, "gray"),
    (contrast, "contrast"),
    (binary, "binary"),
    (morph, "morph")
]:
    res = decode(src, timeout=100)
    if res:
        decoded = res
        print(f"✅ Decode SUCCESS on {name}")
        break

if decoded:
    for d in decoded:
        print("📦 DataMatrix Data:", d.data.decode("utf-8"))
        print("📐 Rect:", d.rect)
else:
    print("❌ Decode FAILED")
