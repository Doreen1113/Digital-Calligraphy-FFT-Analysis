import re

def wrap_text_custom_chars(input_file, output_file, chars_per_line=8):
    try:
        # 1. 讀取檔案
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 2. 使用正則表達式只保留「中文字」
        # \u4e00-\u9fff: 常用漢字
        # \u3400-\u4dbf: 擴展 A 區 (常見於古籍異體字)
        # \u20000-\u2a6df: 擴展 B 區 (若有極罕見古字可視需求開啟)
        chinese_only = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', content)
        clean_content = "".join(chinese_only)
        
        # 3. 依照設定的字數進行切割與換行
        wrapped_content = "\n".join(
            [clean_content[i : i + chars_per_line] for i in range(0, len(clean_content), chars_per_line)]
        )
        
        # 4. 將結果寫入新檔案
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(wrapped_content)
            
        print(f"--- 處理成功 ---")
        print(f"設定每行字數：{chars_per_line}")
        print(f"結果已儲存至：{output_file}")

    except FileNotFoundError:
        print("錯誤：找不到指定的來源檔案，請檢查檔名是否正確。")
    except Exception as e:
        print(f"發生錯誤：{e}")

# --- ⚙️ 使用設定區 ---
input_filename = '10.txt'    # 原始檔案
output_filename = '10.txt'      # 輸出檔案
target_count = 7                # 在這裡修改您想要的「每行字數」👈

wrap_text_custom_chars(input_filename, output_filename, target_count)