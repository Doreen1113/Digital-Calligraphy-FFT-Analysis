import os
import re
import shutil

# --- 路徑設定 ---
AUTO_SPLIT_DIR = r"C:\My_Project\Fourier_drawing\Fonts\03_split_temp" # 自動分割出的圖(已刪除爛圖)
PATCH_DIR = r"C:\My_Project\Fourier_drawing\Fonts\03_patch"          # 你手動補的字 (檔名如 11.png, 17.png)
FINAL_DIR = r"C:\My_Project\Fourier_drawing\Fonts\03_final_font"      # 最終對齊後的結果

def smart_patch_sequencer(total_chars=897):
    if not os.path.exists(FINAL_DIR): os.makedirs(FINAL_DIR)

    # 1. 取得並自然排序自動分割的檔案 (這些是剩下的「好字」)
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
    
    auto_files = [f for f in os.listdir(AUTO_SPLIT_DIR) if f.lower().endswith(('.png', '.jpg'))]
    auto_files.sort(key=natural_sort_key)
    
    # 2. 取得補字清單 (Key 是序號整數)
    patch_map = {}
    if os.path.exists(PATCH_DIR):
        for f in os.listdir(PATCH_DIR):
            match = re.search(r'\d+', f)
            if match:
                patch_map[int(match.group())] = f

    print(f"--- 啟動智慧縫合 ---")
    print(f"自動檔案庫剩餘: {len(auto_files)} 張")
    print(f"手動補位清單: {list(patch_map.keys())}")

    auto_ptr = 0  # 自動檔案的指標
    
    # 3. 依照絕對序號 1 ~ 總字數 進行填充
    for i in range(1, total_chars + 1):
        target_name = f"font_00_{i:04d}.png"
        
        # 情況 A：這個序號有補字，優先插隊
        if i in patch_map:
            src_path = os.path.join(PATCH_DIR, patch_map[i])
            shutil.copy(src_path, os.path.join(FINAL_DIR, target_name))
            print(f"序號 {i:04d} -> [補字插隊] 使用 {patch_map[i]}")
            
        # 情況 B：沒有補字，從自動分割庫拿下一張「正常圖」
        elif auto_ptr < len(auto_files):
            src_path = os.path.join(AUTO_SPLIT_DIR, auto_files[auto_ptr])
            shutil.copy(src_path, os.path.join(FINAL_DIR, target_name))
            # print(f"序號 {i:04d} -> [自動補位] 使用 {auto_files[auto_ptr]}")
            auto_ptr += 1
            
        else:
            print(f"⚠️ 序號 {i:04d} 之後已無可用圖片！")
            break

    print(f"\n✅ 縫合完成！最終成品在: {FINAL_DIR}")
    print(f"提示：如果最後總數不夠，代表你刪掉的爛圖比你補回去的字還多，請檢查原帖是否有漏。")

if __name__ == "__main__":
    # 假設這本字帖總共有 24 個字，你就填 24
    smart_patch_sequencer(total_chars=897)