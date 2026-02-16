import cv2
import numpy as np
import os

# --- 設定路徑 (接續你的裁切結果) ---
INPUT_PATH = r"C:\My_Project\Fourier_drawing\Fonts\03_cropped_color"
BW_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_tmp2"

def generate_no_watermark_bw():
    if not os.path.exists(BW_OUTPUT): os.makedirs(BW_OUTPUT)
    image_files = [f for f in os.listdir(INPUT_PATH) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_files.sort()

    print(f"🚀 啟動「浮水印消除」模式：正在修補筆畫空洞...")

    for img_name in image_files:
        img = cv2.imread(os.path.join(INPUT_PATH, img_name))
        if img is None: continue

        # 1. 🔥 顏色通道處理：取紅色通道 (R)
        # 米字格紅線在 R 通道會變淡，有利於後續處理
        b, g, r_channel = cv2.split(img)

        # 2. 🔥 核心魔法：中值濾波 (Median Blur)
        # 這個步驟會把細小的白色浮水印字跡「抹掉」，使其與背景咖啡色融合
        # 數字 5 或 7 代表強度，若浮水印還在，可試著調到 9
        denoised = cv2.medianBlur(r_channel, 7)

        # 3. 自適應二值化 (Adaptive Threshold)
        # 因為前面抹掉了浮水印，現在二值化就不會產生空洞
        binary = cv2.adaptiveThreshold(
            denoised, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 
            81, # 較大的 BlockSize 確保字體實心
            10  # C 值
        )

        # 4. 🔥 形態學閉運算 (Closing)：填補殘留的微小孔洞
        # 即使還有剩餘的浮水印碎片，這一步會把筆畫內的「白點」強制補滿
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary_solid = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 5. 連通域面積過濾：刪除格子邊緣可能剩下的極小碎片
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_solid, connectivity=8)
        cleaned = np.zeros_like(binary_solid)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] > 150: # 面積過濾
                cleaned[labels == i] = 255

        # 6. 轉回白底黑字並輸出
        final_bw = cv2.bitwise_not(cleaned)
        cv2.imwrite(os.path.join(BW_OUTPUT, f"clean_bw_{img_name}"), final_bw)
        print(f"  ✅ 已消除浮水印並處理: {img_name}")

if __name__ == "__main__":
    generate_no_watermark_bw()