import cv2
import os
from .threshold import process as auto_threshold
from .blur import apply_median_blur as clean_noise

def clean_image(img_path, output_temp="./images/temp_clean.png"):
    """
    一鍵式預處理流水線：
    1. 讀取灰階圖
    2. 中值濾波去噪 (參考 blur.py)
    3. 自動偵測背景極性並二值化 (參考 threshold.py)
    """
    # 讀取灰階圖
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    
    # 建立暫存目錄
    if not os.path.exists("./images"):
        os.makedirs("./images")
    
    # 第一步：去噪 (ksize=1 -> 3x3)
    img_cleaned = clean_noise(img, kernel_size=1)
    
    # 第二步：自動背景偵測、對比增強與二值化
    # 此步驟會自動將白底黑字轉為「黑底白字」，供 FFT 使用
    binary = auto_threshold(img_cleaned)
    
    # 儲存暫存結果供 SVG.py 或 fft.py 讀取
    cv2.imwrite(output_temp, binary)
    
    return binary