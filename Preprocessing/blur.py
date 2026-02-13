import cv2

def apply_median_blur(img, kernel_size=0):
    """
    根據上傳的 blur.py 邏輯執行中值濾波
    final_ksize = kernel_size * 2 + 1
    """
    ksize = kernel_size * 2 + 1
    # 中值濾波對書法雜訊（椒鹽雜訊）效果極佳
    return cv2.medianBlur(img, ksize)