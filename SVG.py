import cv2
import numpy as np

def bitmap_to_contour_svg(input_bitmap_path: str, output_svg_path: str):
    """將影像輪廓（含內部孔洞）轉為純淨的 SVG 路徑"""
    image = cv2.imread(input_bitmap_path)
    if image is None:
        print(f"Error: 找不到圖片 {input_bitmap_path}")
        return
        
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 使用二值化確保輪廓清晰 (THRESH_BINARY_INV 是為了處理白底黑字)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # --- 關鍵修正處 ---
    # 將 cv2.RETR_EXTERNAL 改為 cv2.RETR_LIST
    # RETR_LIST：提取所有輪廓，而不建立任何階層關係
    # RETR_TREE：提取所有輪廓，並建立完整的嵌套階層
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    
    h, w = gray.shape
    with open(output_svg_path, 'w', encoding='utf-8') as f:
        f.write(f'<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n')
        
        for cnt in contours:
            # 過濾太小的雜訊 (可以視情況調整 10 這個數值)
            if len(cnt) < 10: 
                continue 
                
            # 生成 SVG 路徑字串
            # M 代表 Move to (起點), L 代表 Line to (連線), Z 代表 Close path (閉合)
            d_attr = "M " + " L ".join([f"{p[0][0]},{p[0][1]}" for p in cnt]) + " Z"
            f.write(f'  <path d="{d_attr}" fill="none" stroke="black" stroke-width="1" />\n')
            
        f.write('</svg>')