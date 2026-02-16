# tools/3_analyze_common.py
"""分析多個字庫的共用字"""
import sys
sys.path.append('..')
from fonts.config import MY_FONTS, get_all_font_dirs
import pandas as pd
from collections import defaultdict

def analyze_common_chars(min_fonts=2, use_kaggle=False, use_my=True):
    """
    找出多個字庫共有的字
    min_fonts: 至少在幾個字庫中出現
    """
    font_dirs = get_all_font_dirs(use_kaggle, use_my)
    
    # 讀取所有標籤
    char_fonts = defaultdict(set)
    
    for font_info in font_dirs:
        labels_file = font_info['labels']
        if not os.path.exists(labels_file):
            print(f"⚠️  找不到標籤: {labels_file}")
            continue
        
        df = pd.read_csv(labels_file)
        for char in df['character'].unique():
            if char and char != '?':
                char_fonts[char].add(font_info['name'])
    
    # 篩選共用字
    common_chars = {
        char: fonts 
        for char, fonts in char_fonts.items() 
        if len(fonts) >= min_fonts
    }
    
    # 輸出結果
    print(f"\n✅ 至少在 {min_fonts} 個字庫出現的字：{len(common_chars)} 個\n")
    
    # 按覆蓋度排序
    sorted_chars = sorted(common_chars.items(), key=lambda x: len(x[1]), reverse=True)
    
    for char, fonts in sorted_chars[:50]:  # 顯示前50
        print(f"   {char} → {len(fonts)} 個字庫: {', '.join(sorted(fonts))}")
    
    # 保存完整列表
    output_file = './data/myfont_common_chars.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            char: list(fonts) 
            for char, fonts in sorted_chars
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 完整列表已保存: {output_file}")
    return common_chars

if __name__ == "__main__":
    # 🔥 只分析你的4個新字庫
    analyze_common_chars(min_fonts=2, use_kaggle=False, use_my=True)
    
    # 或者：同時分析舊+新字庫
    # analyze_common_chars(min_fonts=3, use_kaggle=True, use_my=True)