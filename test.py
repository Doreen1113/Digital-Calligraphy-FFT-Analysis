import cv2
import numpy as np
import os

# --- 1. 設定路徑 ---
BASE_PATH = r"C:\My_Project\Fourier_drawing\Fonts\03"
CROP_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_cropped_color"
BW_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_original_bw0"

def setup_folders():
    for d in [CROP_OUTPUT, BW_OUTPUT]:
        if not os.path.exists(d):
            os.makedirs(d)

def process_pipeline():
    setup_folders()
    
    # 取得檔案清單
    image_files = [f for f in os.listdir(BASE_PATH) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_files.sort()

    print(f"🚀 開始執行一體化處理，共計 {len(image_files)} 張圖片...")

    for img_name in image_files:
        img_path = os.path.join(BASE_PATH, img_name)
        img = cv2.imread(img_path)
        if img is None: continue

        # --- 第一階段：紅色大矩形框物理裁切 ---
        # 轉換 HSV 抓取紅色
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_red1, upper_red1 = np.array([0, 70, 50]), np.array([10, 255, 255])
        lower_red2, upper_red2 = np.array([170, 70, 50]), np.array([180, 255, 255])
        
        mask = cv2.add(cv2.inRange(hsv, lower_red1, upper_red1), 
                       cv2.inRange(hsv, lower_red2, upper_red2))
        
        # 膨脹紅線並尋找最大輪廓
        mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print(f"  ❌ {img_name}: 找不到紅框，跳過此圖")
            continue

        max_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)
        
        # 物理裁切 (向內縮 offset 避開紅線殘留)
        offset = 1
        cropped_color = img[y+offset : y+h-offset, x+offset : x+w-offset]
        
        # 儲存裁切後的彩色圖供檢查
        cv2.imwrite(os.path.join(CROP_OUTPUT, f"cropped_{img_name}"), cropped_color)

        # --- 第二階段：消除浮水印與高品質黑白化 ---
        # 1. 顏色通道分離，取紅色通道以淡化紅格線
        _, _, r_channel = cv2.split(cropped_color)

        # 2. 中值濾波：關鍵步驟，將細小的白色浮水印字跡抹除
        # 💡 若浮水印較大，可將 7 改為 9
        denoised = cv2.medianBlur(r_channel, 7)

        # 3. 自適應二值化：確保筆畫實心
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 81, 10
        )

        # 4. 形態學閉運算：填補浮水印消失後在筆畫上留下的微小孔洞
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary_solid = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 5. 連通域面積過濾：刪除浮水印殘留的微小碎片
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_solid, connectivity=8)
        cleaned = np.zeros_like(binary_solid)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] > 150:
                cleaned[labels == i] = 255

        # 6. 最終輸出：轉回白底黑字
        final_bw = cv2.bitwise_not(cleaned)
        cv2.imwrite(os.path.join(BW_OUTPUT, f"final_bw_{img_name}"), final_bw)
        
        print(f"  ✅ 處理完成: {img_name} -> 物理裁切 + 浮水印掃除")

    print(f"\n🎉 全部流程執行完畢！")
    print(f"📁 彩色裁切檔：{CROP_OUTPUT}")
    print(f"📁 最終黑白底圖：{BW_OUTPUT}")

if __name__ == "__main__":
    process_pipeline()