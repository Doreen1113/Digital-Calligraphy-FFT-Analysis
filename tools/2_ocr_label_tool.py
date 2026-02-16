# tools/2_create_labels.py
"""
為字庫創建標籤檔案
- 00, 02, 03: 根據 XX.txt 按順序分配
- 01: 使用 OCR 識別
"""
import os
import csv
from pathlib import Path

# ============ 配置 ============
BASE_DIR = r"C:\My_Project\Fourier_drawing\Fonts\my_fonts"

FONT_CONFIG = {
    '00': {
        'name': '智永',
        'text_file': r"C:\My_Project\Fourier_drawing\Fonts\00.txt",
        'use_ocr': False
    },
    '01': {
        'name': '沈尹默',
        'text_file': None,
        'use_ocr': True
    },
    '02': {
        'name': '顏真卿',
        'text_file': r"C:\My_Project\Fourier_drawing\Fonts\02.txt",
        'use_ocr': False
    },
    '03': {
        'name': '歐陽詢',
        'text_file': r"C:\My_Project\Fourier_drawing\Fonts\03.txt",
        'use_ocr': False
    }
}

# ============ OCR 相關 ============
_ocr_instance = None

def get_ocr():
    """獲取OCR實例（只在需要時初始化）"""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            import easyocr
            print("正在初始化 EasyOCR...")
            _ocr_instance = easyocr.Reader(['ch_tra', 'en'], gpu=False, verbose=False)
            print("✅ EasyOCR 初始化完成\n")
        except ImportError:
            print("❌ 請先安裝: pip install easyocr")
            return None
    return _ocr_instance

def ocr_single_image(image_path: str) -> tuple:
    """識別單張圖片，返回 (字, 信心度)"""
    ocr = get_ocr()
    if ocr is None:
        return None, 0
    
    try:
        results = ocr.readtext(image_path)
        if results and len(results) > 0:
            text = results[0][1]
            confidence = results[0][2]
            char = text[0] if len(text) > 0 else text
            return char, confidence
        return None, 0
    except Exception as e:
        return None, 0

# ============ 從文字檔讀取字序 ============
def load_text_sequence(text_file):
    """
    從 XX.txt 讀取字序
    處理格式：天地玄黃　宇宙洪荒
    """
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除空白、換行、標點，只保留中文字
    chars = []
    for char in content:
        if '\u4e00' <= char <= '\u9fff':  # 中文字範圍
            chars.append(char)
    
    return chars

# ============ 主要處理函式 ============
def create_labels_for_font(font_id):
    """為指定字庫創建標籤"""
    
    config = FONT_CONFIG[font_id]
    font_dir = os.path.join(BASE_DIR, font_id)
    output_csv = os.path.join(font_dir, 'labels.csv')
    
    if not os.path.exists(font_dir):
        print(f"❌ 目錄不存在: {font_dir}")
        return
    
    # 獲取所有圖片並排序
    image_files = sorted([
        f for f in os.listdir(font_dir) 
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    
    if not image_files:
        print(f"❌ {font_id} 沒有找到圖片")
        return
    
    print(f"\n{'='*60}")
    print(f"處理字庫: {font_id} - {config['name']}")
    print(f"圖片數量: {len(image_files)}")
    print(f"{'='*60}\n")
    
    results = []
    
    # === 方法1: 根據文字檔按順序分配 ===
    if not config['use_ocr']:
        if not config['text_file'] or not os.path.exists(config['text_file']):
            print(f"❌ 找不到文字檔: {config['text_file']}")
            return
        
        chars = load_text_sequence(config['text_file'])
        print(f"📖 從文字檔讀取到 {len(chars)} 個字")
        
        if len(chars) < len(image_files):
            print(f"⚠️  警告: 文字數({len(chars)}) < 圖片數({len(image_files)})")
            print(f"   將只標註前 {len(chars)} 張圖片")
        
        for idx, img_name in enumerate(image_files):
            if idx < len(chars):
                char = chars[idx]
                conf = 1.0  # 人工指定
                status = "✓"
            else:
                char = "?"
                conf = 0.0
                status = "⚠️"
            
            results.append({
                'filename': img_name,
                'character': char,
                'confidence': f"{conf:.4f}"
            })
            
            print(f"[{idx+1:4d}/{len(image_files)}] {status} {img_name:30s} → {char}")
    
    # === 方法2: 使用 OCR 識別 ===
    else:
        print(f"🔍 使用 OCR 自動識別...\n")
        success = 0
        fail = 0
        low_confidence = []
        
        for idx, img_name in enumerate(image_files, 1):
            img_path = os.path.join(font_dir, img_name)
            char, conf = ocr_single_image(img_path)
            
            if char:
                results.append({
                    'filename': img_name,
                    'character': char,
                    'confidence': f"{conf:.4f}"
                })
                
                status = "✓" if conf > 0.8 else "⚠️"
                print(f"[{idx:4d}/{len(image_files)}] {status} {img_name:30s} → {char} ({conf:.2%})")
                
                if conf < 0.8:
                    low_confidence.append((img_name, char, conf))
                success += 1
            else:
                results.append({
                    'filename': img_name,
                    'character': '?',
                    'confidence': '0.0000'
                })
                print(f"[{idx:4d}/{len(image_files)}] ❌ {img_name:30s} → 識別失敗")
                fail += 1
        
        # OCR 統計
        print(f"\n   成功: {success}/{len(image_files)} ({success/len(image_files)*100:.1f}%)")
        print(f"   失敗: {fail}")
        print(f"   低信心度(<80%): {len(low_confidence)}")
        
        if low_confidence:
            print(f"\n⚠️  需要人工檢查 (前10個):")
            for fname, char, conf in low_confidence[:10]:
                print(f"   {fname} → {char} ({conf:.2%})")
    
    # 保存 CSV
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'character', 'confidence'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ 已保存: {output_csv}")
    return output_csv

# ============ 批量處理所有字庫 ============
def process_all_fonts():
    """處理所有字庫"""
    print("\n🚀 開始批量創建標籤...")
    
    for font_id in sorted(FONT_CONFIG.keys()):
        try:
            create_labels_for_font(font_id)
        except Exception as e:
            print(f"\n❌ 處理 {font_id} 時出錯: {e}\n")
            continue
    
    print("\n" + "="*60)
    print("✅ 全部完成！")
    print("="*60)
    
    print("\n📊 生成的標籤檔案:")
    for font_id in FONT_CONFIG.keys():
        label_file = os.path.join(BASE_DIR, font_id, 'labels.csv')
        if os.path.exists(label_file):
            with open(label_file, 'r', encoding='utf-8') as f:
                lines = sum(1 for _ in f) - 1  # 減去標題行
            print(f"   {font_id}/labels.csv → {lines} 個標籤")
    
    print("\n💡 下一步:")
    print("   1. 檢查 01/labels.csv (OCR結果)")
    print("   2. 執行: python tools/3_analyze_common_chars.py")

# 只處理 01 (OCR)
if __name__ == "__main__":
    create_labels_for_font('01')
