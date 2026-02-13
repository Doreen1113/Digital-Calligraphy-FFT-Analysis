import cv2
import numpy as np

def process(img_gray, multiply_factor=1.25):
    """
    根據上傳的 threshold.py 邏輯：
    1. 增強對比
    2. 自動偵測背景黑白並反轉
    3. 執行二值化
    """
    # 增強對比度
    img = cv2.multiply(img_gray, np.array([multiply_factor]))

    height, width = img.shape[0:2]
    cnt_black = 0
    cnt_white = 0
    
    # 檢查邊界像素
    for row in range(height):
        for col in [0, width-1]:
            if img[row, col] > 127: cnt_white += 1
            else: cnt_black += 1
    for col in range(width):
        for row in [0, height-1]:
            if img[row, col] > 127: cnt_white += 1
            else: cnt_black += 1
            
    # 如果背景是白的，反轉成黑底白字
    if cnt_black < cnt_white:
        img = 255 - img
    
    # 執行二值化 (參考原檔邏輯)
    _, binary = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY)
    return binary