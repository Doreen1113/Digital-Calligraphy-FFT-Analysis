import cv2
import numpy as np
import os

# --- 設定路徑 ---
BASE_PATH = r"C:\My_Project\Fourier_drawing\Fonts\03" 
SPLIT_OUTPUT = r"C:\My_Project\Fourier_drawing\Fonts\03_split_temp1"

def run_simple_line_erase_split(rows=4, cols=2, line_thickness=3):
    if not os.path.exists(SPLIT_OUTPUT): 
        os.makedirs(SPLIT_OUTPUT)

    image_files = [f for f in os.listdir(BASE_PATH) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_files.sort()

    char_global_count = 1
    canvas_size = 512

    print(f"🚀 啟動簡單去線模式：行列設定 ({rows}x{cols})")

    for img_name in image_files:
        img_path = os.path.join(BASE_PATH, img_name)
        img = cv2.imread(img_path)
        if img is None: continue
        
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. 轉為黑白圖 (分析基礎)
        if np.mean(gray) > 127:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 2. 🔥 強力抹除線條 (開運算)
        # line_thickness 越大，抹除越強。預設 3 適合細線，5 適合粗一點的格子線。
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_thickness, line_thickness))
        binary_cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        # 3. 均分切割
        cell_h = h // rows
        cell_w = w // cols

        for c in range(cols - 1, -1, -1): # 由右至左
            for r in range(rows):         # 由上至下
                y1, y2 = r * cell_h, (r + 1) * cell_h
                x1, x2 = c * cell_w, (c + 1) * cell_w
                
                # 取得格子區塊
                cell = binary_cleaned[y1:y2, x1:x2]

                # 4. 置中縮放輸出 (白底黑字)
                canvas = np.full((canvas_size, canvas_size), 255, dtype=np.uint8)
                coords = cv2.findNonZero(cell)

                if coords is not None:
                    bx, by, bw, bh = cv2.boundingRect(coords)
                    char_extract = cell[by:by+bh, bx:bx+bw]
                    
                    # 轉為白底黑字
                    char_black = cv2.bitwise_not(char_extract)
                    
                    scale = min(440/bw, 440/bh)
                    nw, nh = int(bw*scale), int(bh*scale)
                    
                    if nw > 0 and nh > 0:
                        resized = cv2.resize(char_black, (nw, nh), interpolation=cv2.INTER_AREA)
                        oy, ox = (canvas_size - nh) // 2, (canvas_size - nw) // 2
                        canvas[oy:oy+nh, ox:ox+nw] = resized

                # 5. 儲存單字
                cv2.imwrite(os.path.join(SPLIT_OUTPUT, f"char_{char_global_count:04d}.png"), canvas)
                char_global_count += 1

    print(f"\n✅ 處理完成！已抹除細線並完成等比例切割。")

if __name__ == "__main__":
    # rows: 橫排數量, cols: 直排數量
    # line_thickness: 抹除強度 (建議 3 或 5)
    run_simple_line_erase_split(rows=4, cols=2, line_thickness=4)