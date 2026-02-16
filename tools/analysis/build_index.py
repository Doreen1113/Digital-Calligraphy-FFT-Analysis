"""建立字庫索引工具"""
import os
import sys
import json
from collections import defaultdict
from pathlib import Path

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
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
        print(f"\n分析: {display_name}")

        try:
            stats = loader.get_statistics(name)
            df = loader.load_labels(name)

            fonts_index["calligraphers"][name] = {
                "id": cal['id'],
                "display_name": cal['display_name'],
                "dynasty": cal['dynasty'],
                "style": cal['style'],
                "description": cal['description'],
                "total_images": stats['total_images'],
                "unique_characters": stats['unique_characters'],
                "avg_confidence": stats['avg_confidence'],
                "image_dir": cal['image_dir'],
                "labels_file": cal['labels_file'],
                "character_list": df['character'].tolist()
            }

            print(f"  [OK] 總圖片: {stats['total_images']}")
            print(f"  [OK] 獨特字: {stats['unique_characters']}")

        except Exception as e:
            print(f"  [Error] 錯誤: {e}")

    # 儲存索引
    index_path = config.get_index_path('fonts_index')
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
        print(f"\n掃描: {display_name}")

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
                    "confidence": row.get('confidence', 1.0)
                })

            print(f"  [OK] 已掃描 {len(df)} 個字")

        except Exception as e:
            print(f"  [Error] 錯誤: {e}")

    # 統計結果
    print("\n" + "-"*70)
    print("統計結果:")
    print("-"*70)

    total_unique_chars = len(character_map)
    calligrapher_names = [cal['name'] for cal in loader.calligraphers]
    common_chars = []

    # 找出所有書法家都有的字
    for char, cals in character_map.items():
        if len(cals) == len(calligrapher_names):
            common_chars.append(char)

    print(f"總獨特字數: {total_unique_chars}")
    print(f"所有書法家共有的字: {len(common_chars)}")

    # 統計每個書法家有多少字
    for cal in loader.calligraphers:
        name = cal['name']
        display_name = cal['display_name']
        count = sum(1 for char_cals in character_map.values() if name in char_cals)
        print(f"  {display_name}: {count} 個字")

    # 建立索引結構
    character_index = {
        "version": "2.0",
        "total_unique_characters": total_unique_chars,
        "total_common_characters": len(common_chars),
        "calligraphers": calligrapher_names,
        "common_characters": sorted(common_chars),
        "character_map": {}
    }

    # 只保存有 2 位以上書法家的字（節省空間）
    for char, cals in character_map.items():
        if len(cals) >= 2:
            character_index["character_map"][char] = cals

    # 儲存索引
    index_path = config.get_index_path('character_index')

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(character_index, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 同字索引已儲存: {index_path}")
    print(f" 索引包含 {len(character_index['character_map'])} 個可比對的字")

    return character_index


def print_summary(fonts_index, character_index):
    """列印摘要報告"""
    print("\n" + "="*70)
    print(" 索引建立完成！摘要報告")
    print("="*70)

    print(f"\n 字庫總覽:")
    print(f"  - 書法家數量: {fonts_index['total_calligraphers']}")

    for name, info in fonts_index['calligraphers'].items():
        print(f"\n  【{info['display_name']}】({info['dynasty']})")
        print(f"    圖片數: {info['total_images']}")
        print(f"    獨特字: {info['unique_characters']}")

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
