import cv2
import numpy as np
import os

# --- 1. 設定路徑 ---
BASE_PATH = r"C:\My_Project\Fourier_drawing\Fonts\03"
CROP_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_cropped_color"
BW_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_original_bw"
SPLIT_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_split_temp"

# --- 2. 核心參數調整 ---
PADDING_V = 25    # 上下方額外留白空間 (解決切到字的問題)
PADDING_H = 10    # 左右方額外留白空間
ROWS = 4          # 字帖行數
COLS = 2          # 字帖列數
CANVAS_SIZE = 512 # 輸出單字圖尺寸

def setup_folders():
    for d in [CROP_OUTPUT, BW_OUTPUT, SPLIT_OUTPUT]:
        if not os.path.exists(d):
            os.makedirs(d)

def run_full_pipeline():
    setup_folders()
    
    image_files = [f for f in os.listdir(BASE_PATH) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_files.sort()

    char_global_count = 1

    print(f"🚀 啟動終極流水線：裁切 -> 去浮水印 -> 黑白化 -> 4x2 分割...")

    for img_name in image_files:
        img_path = os.path.join(BASE_PATH, img_name)
        img = cv2.imread(img_path)
        if img is None: continue
        img_h, img_w = img.shape[:2]

        # --- 第一階段：物理定位與紅框裁切 ---
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_red1, upper_red1 = np.array([0, 70, 50]), np.array([10, 255, 255])
        lower_red2, upper_red2 = np.array([170, 70, 50]), np.array([180, 255, 255])
        mask = cv2.add(cv2.inRange(hsv, lower_red1, upper_red1), 
                       cv2.inRange(hsv, lower_red2, upper_red2))
        
        mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print(f"  ❌ {img_name}: 找不到紅框，跳過")
            continue

        max_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)
        
        # 增加緩衝區裁切
        y1, y2 = max(0, y - PADDING_V), min(img_h, y + h + PADDING_V)
        x1, x2 = max(0, x - PADDING_H), min(img_w, x + w + PADDING_H)
        cropped_color = img[y1:y2, x1:x2]
        cv2.imwrite(os.path.join(CROP_OUTPUT, f"cropped_{img_name}"), cropped_color)

        # --- 第二階段：高品質去噪與黑白化 ---
        _, _, r_channel = cv2.split(cropped_color)
        
        # 中值濾波消滅白色浮水印字跡
        denoised = cv2.medianBlur(r_channel, 7)
        
        # 自適應二值化 (保住泉字細線)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 81, 10
        )
        
        # 閉運算填補筆畫孔洞
        binary_solid = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        
        # 面積過濾去除殘餘碎線
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_solid, connectivity=8)
        binary_final = np.zeros_like(binary_solid)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] > 180: # 面積過濾門檻
                binary_final[labels == i] = 255
        
        # 儲存完整的去邊黑白底圖 (白底黑字)
        bw_full = cv2.bitwise_not(binary_final)
        cv2.imwrite(os.path.join(BW_OUTPUT, f"clean_bw_{img_name}"), bw_full)

        # --- 第三階段：4x2 等比例分割與單字置中 ---
        roi_h, roi_w = binary_final.shape
        cell_h = roi_h // ROWS
        cell_w = roi_w // COLS

        # 順序：由右至左 (C 從大到小)，由上至下 (R 從小到大)
        for c in range(COLS - 1, -1, -1):
            for r in range(ROWS):
                cy1, cy2 = r * cell_h, (r + 1) * cell_h
                cx1, cx2 = c * cell_w, (c + 1) * cell_w
                
                cell = binary_final[cy1:cy2, cx1:cx2]
                
                # 格內主體提取與置中
                canvas = np.full((CANVAS_SIZE, CANVAS_SIZE), 255, dtype=np.uint8)
                coords = cv2.findNonZero(cell)
                
                if coords is not None:
                    bx, by, bw, bh = cv2.boundingRect(coords)
                    char_extract = cell[by:by+bh, bx:bx+bw]
                    char_black = cv2.bitwise_not(char_extract)
                    
                    # 縮放至 512 畫布，預留 15% 邊距
                    scale = min(440/bw, 440/bh)
                    nw, nh = int(bw*scale), int(bh*scale)
                    
                    if nw > 0 and nh > 0:
                        resized = cv2.resize(char_black, (nw, nh), interpolation=cv2.INTER_AREA)
                        oy, ox = (CANVAS_SIZE - nh) // 2, (CANVAS_SIZE - nw) // 2
                        canvas[oy:oy+nh, ox:ox+nw] = resized

                # 儲存單字圖
                cv2.imwrite(os.path.join(SPLIT_OUTPUT, f"char_{char_global_count:04d}.png"), canvas)
                char_global_count += 1
        
        print(f"  ✅ {img_name} 處理完畢，已生成 {ROWS*COLS} 個單字")

    print(f"\n🎉 任務圓滿完成！")
    print(f"📂 單字圖儲存於: {SPLIT_OUTPUT}")

if __name__ == "__main__":
    run_stage_1 = run_full_pipeline() # 執行總流程