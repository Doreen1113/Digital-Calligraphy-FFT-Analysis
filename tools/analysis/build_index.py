"""建立字庫索引工具"""
import os
import sys
import json
from collections import defaultdict
from pathlib import Path

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    import codecs
    # 檢查 stdout 是否已經是 codecs writer（避免重複包裝）
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils import get_config, FontDataLoader

def build_fonts_index():
    """建立字庫總索引"""
    print("\n" + "="*70)
    print(" 建立字庫總索引")
    print("="*70)

    loader = FontDataLoader()
    config = get_config()

    fonts_index = {
        "version": "2.0",
        "total_calligraphers": len(loader.calligraphers),
        "calligraphers": {}
    }

    for cal in loader.calligraphers:
        name = cal['name']
        display_name = cal['display_name']
        book = cal.get('book', '')
        label = f"{display_name}·{book}" if book else display_name
        print(f"\n分析: {label}")

        try:
            stats = loader.get_statistics(name)
            df = loader.load_labels(name)

            fonts_index["calligraphers"][name] = {
                "id": cal['id'],
                "display_name": cal['display_name'],
                "book": cal.get('book', ''),
                "dynasty": cal['dynasty'],
                "style": cal['style'],
                "description": cal['description'],
                "total_images": stats['total_images'],
                "unique_characters": stats['unique_characters'],
                "avg_confidence": stats['avg_confidence'],
                "image_dir": loader._resolve(cal['image_dir']),
                "labels_file": loader._resolve(cal['labels_file']),
                "character_list": df['character'].tolist()
            }

            print(f"  [OK] 總圖片: {stats['total_images']}")
            print(f"  [OK] 獨特字: {stats['unique_characters']}")

        except Exception as e:
            print(f"  [Error] 錯誤: {e}")

    # 儲存索引（路徑解析為絕對路徑，不受 CWD 影響）
    index_path = loader._resolve(config.get_index_path('fonts_index'))
    os.makedirs(os.path.dirname(index_path), exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(fonts_index, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 字庫索引已儲存: {index_path}")
    return fonts_index


def build_character_index():
    """建立同字索引（找出所有書法家共有的字）"""
    print("\n" + "="*70)
    print(" 建立同字索引")
    print("="*70)

    loader = FontDataLoader()
    config = get_config()

    # 統計每個字在哪些書法家的字庫中出現
    character_map = defaultdict(dict)

    for cal in loader.calligraphers:
        name = cal['name']
        display_name = cal['display_name']
        book = cal.get('book', '')
        label = f"{display_name}·{book}" if book else display_name
        print(f"\n掃描: {label}")

        try:
            df = loader.load_labels(name)

            for idx, row in df.iterrows():
                char = row['character']
                filename = row['filename']

                # 記錄這個字在這位書法家的字庫中的檔名
                if char not in character_map:
                    character_map[char] = {}

                if name not in character_map[char]:
                    character_map[char][name] = []

                character_map[char][name].append({
                    "filename": filename,
                    "image_path": loader.get_image_path(name, filename),
                    "confidence": row.get('confidence', 1.0),
                    "book": cal.get('book', ''),      # 字帖名稱
                    "font_id": cal['id'],             # 資料夾編號
                })

            print(f"  [OK] 已掃描 {len(df)} 個字")

        except Exception as e:
            print(f"  [Error] 錯誤: {e}")

    # 統計結果
    print("\n" + "-"*70)
    print("統計結果:")
    print("-"*70)

    total_unique_chars = len(character_map)

    # name → display_name 對應表
    name_to_display = {cal['name']: cal['display_name'] for cal in loader.calligraphers}

    # 不重複書法家清單（保留順序）
    seen = {}
    for cal in loader.calligraphers:
        dn = cal['display_name']
        if dn not in seen:
            seen[dn] = []
        seen[dn].append(cal['name'])
    unique_display_names = list(seen.keys())          # e.g. ['智永','沈尹默','顏真卿',...]
    display_to_names     = seen                        # display_name → [name, name2, ...]

    # 找出所有書法家（以 display_name 合併）都有的字
    all_display_set = set(unique_display_names)
    common_chars = []
    for char, cals in character_map.items():
        char_displays = set(name_to_display[n] for n in cals.keys())
        if char_displays >= all_display_set:
            common_chars.append(char)

    print(f"總獨特字數: {total_unique_chars}")
    print(f"所有書法家共有的字: {len(common_chars)}")

    # 統計每位書法家（合併多本字帖）有多少獨特字
    for display_name in unique_display_names:
        names = display_to_names[display_name]
        # 取各本字帖的聯集
        char_set = set(
            char for char, cals in character_map.items()
            if any(n in cals for n in names)
        )
        print(f"  {display_name}: {len(char_set)} 個字")

    # 建立索引結構
    all_names = [cal['name'] for cal in loader.calligraphers]
    character_index = {
        "version": "2.0",
        "total_unique_characters": total_unique_chars,
        "total_common_characters": len(common_chars),
        "calligraphers": all_names,
        "common_characters": sorted(common_chars),
        "character_map": {}
    }

    # 只保存有 2 位以上書法家（display_name 不同）的字（節省空間）
    for char, cals in character_map.items():
        char_displays = set(name_to_display[n] for n in cals.keys())
        if len(char_displays) >= 2:
            character_index["character_map"][char] = cals

    # 儲存索引（路徑解析為絕對路徑）
    index_path = loader._resolve(config.get_index_path('character_index'))

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(character_index, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 同字索引已儲存: {index_path}")
    print(f" 索引包含 {len(character_index['character_map'])} 個可比對的字")

    return character_index


def print_summary(fonts_index, character_index):
    """列印摘要報告（按書法家分組，同一書法家多本字帖合併顯示）"""
    from collections import defaultdict

    print("\n" + "="*70)
    print(" 索引建立完成！摘要報告")
    print("="*70)

    # 按 display_name 分組（同一書法家可能有多本字帖）
    cal_groups = defaultdict(list)
    for name, info in fonts_index['calligraphers'].items():
        cal_groups[info['display_name']].append(info)

    total_books = len(fonts_index['calligraphers'])
    total_cals  = len(cal_groups)

    print(f"\n 字庫總覽（不重複書法家）:")
    print(f"  - 書法家數量: {total_cals} 位 / 字帖數量: {total_books} 本")

    for display_name, books in cal_groups.items():
        dynasty = books[0].get('dynasty', '')
        total_images = sum(b['total_images'] for b in books)
        print(f"\n  【{display_name}】({dynasty})")
        if len(books) == 1:
            b = books[0]
            book_name = b.get('book', '')
            prefix = f"〔{book_name}〕 " if book_name else ""
            print(f"    {prefix}圖片數: {b['total_images']}　獨特字: {b['unique_characters']}")
        else:
            print(f"    共 {len(books)} 本字帖，合計圖片: {total_images}")
            for b in books:
                book_name = b.get('book', '未知字帖')
                print(f"    ├─ 〔{book_name}〕 圖片: {b['total_images']}　獨特字: {b['unique_characters']}")

    print(f"\n 同字索引:")
    print(f"  - 總獨特字數: {character_index['total_unique_characters']}")
    print(f"  - 所有書法家共有: {character_index['total_common_characters']} 個字")
    print(f"  - 可比對字數: {len(character_index['character_map'])} 個")

    if character_index['common_characters']:
        print(f"\n  前 20 個共有字:")
        print(f"  {' '.join(character_index['common_characters'][:20])}")

    print("\n" + "="*70)


if __name__ == "__main__":
    print("\n[INFO] Starting index build...")

    # 建立字庫索引
    fonts_idx = build_fonts_index()

    # 建立同字索引
    char_idx = build_character_index()

    # 列印摘要
    print_summary(fonts_idx, char_idx)

    print("\n[OK] 所有索引建立完成！")
    print("="*70 + "\n")
