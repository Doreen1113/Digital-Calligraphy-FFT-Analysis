# Preprocessing/cleaner.py
import cv2
import numpy as np

def get_clean_binary(img_path):
    # 整合 threshold.py 邏輯
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.multiply(img, np.array([1.25]))
    
    # 自動偵測背景並反轉 (確保為黑底白字)
    h, w = img.shape
    edge_pixels = np.concatenate([img[0,:], img[-1,:], img[:,0], img[:,-1]])
    if np.mean(edge_pixels) > 127:
        img = 255 - img
    
    # 降噪處理
    img = cv2.medianBlur(img, 3)
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    return binary