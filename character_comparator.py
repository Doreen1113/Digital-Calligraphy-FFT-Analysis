"""
Character Comparison Tool
Compare how different calligraphers write the same character
"""
import os
import sys
import json
import cv2
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    # 檢查 stdout 是否已經是 codecs writer（避免重複包裝）
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(__file__))

from src.utils import get_config, FontDataLoader

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def _resolve_img_path(raw: str) -> str:
    """將 character_index 中的路徑轉換為當前環境可用的路徑。

    索引可能存 Windows 絕對路徑（C:/My_Project/...），
    在 Linux/Docker 上需自動對應到 Fonts/my_fonts/ 下的相對路徑。
    """
    norm = raw.replace("\\", "/")
    if os.path.exists(norm):
        return norm
    for marker in ("Fonts/my_fonts/", "data/fonts/"):
        if marker in norm:
            rel = norm.split(marker, 1)[-1]
            candidate = os.path.join(_PROJECT_ROOT, marker, rel)
            candidate = os.path.normpath(candidate)
            if os.path.exists(candidate):
                return candidate
    return norm

# Matplotlib configuration for Chinese characters
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'sans-serif']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

try:
    import matplotlib
    matplotlib.font_manager._rebuild()
except:
    pass


_font_prop_cache = None

def _get_font_prop():
    """Get proper font for CJK rendering, with Windows direct path priority"""
    global _font_prop_cache
    if _font_prop_cache is not None:
        return _font_prop_cache

    # Known CJK font paths (Windows & Linux)
    _known = [
        r'C:\Windows\Fonts\msyh.ttc',
        r'C:\Windows\Fonts\simsun.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]

    for path in _known:
        p = path.replace('\\', os.sep).replace('/', os.sep)
        if os.path.exists(p):
            try:
                prop = fm.FontProperties(fname=p)
                _font_prop_cache = prop
                return prop
            except Exception:
                continue

    # Fallback: scan system fonts (exclude variable fonts)
    _cjk_kw = ['msyh', 'simhei', 'simsun', 'kaiti', 'wqy', 'notosans']
    for path in fm.findSystemFonts():
        lower = path.lower()
        if any(kw in lower for kw in _cjk_kw) and '-vf' not in lower:
            try:
                prop = fm.FontProperties(fname=path)
                _font_prop_cache = prop
                return prop
            except Exception:
                continue

    # Last resort: use default
    _font_prop_cache = fm.FontProperties()
    return _font_prop_cache


def load_character_index():
    """Load character index from file"""
    config = get_config()
    index_path = config.get_index_path('character_index')

    if not os.path.exists(index_path):
        print(f"[Error] Character index not found: {index_path}")
        print("Please run: py tools/analysis/build_index.py")
        return None

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_available_characters():
    """Get list of all characters that can be compared"""
    char_index = load_character_index()
    if not char_index:
        return []

    # Return characters that have at least 2 calligraphers
    char_map = char_index.get('character_map', {})
    return sorted(char_map.keys())


def get_common_characters():
    """Get list of characters all 4 calligraphers have"""
    char_index = load_character_index()
    if not char_index:
        return []

    return char_index.get('common_characters', [])


def compare_character(character, output_path=None, selected_calligraphers=None):
    """
    Compare how different calligraphers write the same character

    Args:
        character: Chinese character to compare
        output_path: Optional path to save comparison image
        selected_calligraphers: List of calligrapher display names to include (optional, if None shows all)
    """
    char_index = load_character_index()
    if not char_index:
        return

    char_map = char_index.get('character_map', {})

    if character not in char_map:
        print(f"[Error] Character '{character}' not found in index")
        print(f"Available characters: {len(char_map)}")
        return

    calligraphers = char_map[character]
    num_cals = len(calligraphers)

    # 載入 display_name 對應
    loader = FontDataLoader()
    name_to_display = {cal['name']: cal['display_name'] for cal in loader.calligraphers}

    print(f"\n{'='*70}")
    print(f" 比對字元: {character}")
    print(f"{'='*70}")
    if selected_calligraphers:
        print(f" 選中的書法家: {', '.join(selected_calligraphers)}")
    print(f" 找到 {num_cals} 位書法家:")

    # Load images
    images = {}
    for cal_name, instances in calligraphers.items():
        display_name = name_to_display.get(cal_name, cal_name)

        # If selected_calligraphers is specified, skip non-selected ones
        if selected_calligraphers and display_name not in selected_calligraphers:
            continue

        # Use the first instance
        if instances:
            img_path = _resolve_img_path(instances[0]['image_path'])
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    images[display_name] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    print(f"   - {display_name:10s}: {os.path.basename(img_path)}")
                else:
                    print(f"   - {display_name:10s}: [Warning] 載入圖片失敗")
            else:
                print(f"   - {display_name:10s}: [Error] 檔案不存在")

    if not images:
        print("[Error] 無法載入任何圖片")
        return

    # Create comparison figure
    num_images = len(images)
    cols = min(4, num_images)
    rows = (num_images + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 4*rows))

    if num_images == 1:
        axes = [axes]
    elif rows == 1:
        axes = axes
    else:
        axes = axes.flatten()

    font_prop = _get_font_prop()
    for idx, (display_name, img) in enumerate(sorted(images.items())):
        ax = axes[idx] if num_images > 1 else axes[0]
        ax.imshow(img, cmap='gray')
        ax.set_title(f"{display_name}", fontsize=14, fontweight='bold', fontproperties=font_prop)
        ax.axis('off')

    # Hide extra subplots
    for idx in range(num_images, len(axes)):
        axes[idx].axis('off')

    # 移除標題，使圖片更清潔
    # plt.suptitle(f'字形比對: "{character}"', fontsize=18, fontweight='bold')
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\n[OK] 比對圖已儲存: {output_path}")
        plt.close()
    else:
        plt.show()

    print(f"{'='*70}\n")


def list_characters_by_count():
    """List characters grouped by how many calligraphers wrote them"""
    char_index = load_character_index()
    if not char_index:
        return

    char_map = char_index.get('character_map', {})

    # Group by count
    by_count = {}
    for char, cals in char_map.items():
        count = len(cals)
        if count not in by_count:
            by_count[count] = []
        by_count[count].append(char)

    print(f"\n{'='*70}")
    print(" Characters by Calligrapher Count")
    print(f"{'='*70}")

    for count in sorted(by_count.keys(), reverse=True):
        chars = by_count[count]
        print(f"\n {count} 位書法家共有 ({len(chars)} 個字):")
        print(f"   {''.join(chars[:50])}")
        if len(chars) > 50:
            print(f"   ... 還有 {len(chars) - 50} 個字")

    print(f"{'='*70}\n")


def interactive_mode():
    """Interactive character comparison mode"""
    print("\n" + "="*70)
    print(" 同字比對工具（互動模式）")
    print("="*70)

    char_index = load_character_index()
    if not char_index:
        return

    common_chars = char_index.get('common_characters', [])
    total_chars = len(char_index.get('character_map', {}))

    print(f"\n 可比對字數: {total_chars}")
    print(f" 四位書法家共有: {len(common_chars)} 個字")

    if common_chars:
        print(f"\n 共有字（前 35 個）:")
        print(f"   {''.join(common_chars[:35])}")

    print(f"\n{'='*70}")
    print(" 指令說明:")
    print("   [字元]     - 比對指定字（例如：天）")
    print("   list      - 依書法家數量列出字元")
    print("   common    - 顯示所有共有字")
    print("   quit/exit - 離開")
    print(f"{'='*70}\n")

    while True:
        try:
            user_input = input("輸入字元或指令: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n離開...")
                break

            if user_input.lower() == 'list':
                list_characters_by_count()
                continue

            if user_input.lower() == 'common':
                print(f"\n 所有共有字 ({len(common_chars)} 個):")
                for i in range(0, len(common_chars), 20):
                    print(f"   {''.join(common_chars[i:i+20])}")
                print()
                continue

            # Assume it's a character
            if len(user_input) == 1:
                output_path = f"./output/comparison_{user_input}.png"
                compare_character(user_input, output_path)
            else:
                print(f"[Error] 請輸入單一字元")

        except KeyboardInterrupt:
            print("\n\n離開...")
            break
        except Exception as e:
            print(f"[Error] {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Command line mode
        character = sys.argv[1]

        if character == '--list':
            list_characters_by_count()
        elif character == '--common':
            common = get_common_characters()
            print(f"\n Common characters ({len(common)}):")
            for i in range(0, len(common), 20):
                print(f"   {''.join(common[i:i+20])}")
            print()
        else:
            output_path = f"./output/comparison_{character}.png"
            compare_character(character, output_path)
    else:
        # Interactive mode
        interactive_mode()
