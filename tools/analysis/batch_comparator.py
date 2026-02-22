"""
批次同字比對工具
一次比對多個字元，產生比對圖或 PDF 報告
"""
import os
import sys
import json
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

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from typing import List, Dict, Optional

from src.utils import get_config, FontDataLoader

# 設定 matplotlib 中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'sans-serif']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False
try:
    import matplotlib
    matplotlib.font_manager._rebuild()
except:
    pass


def load_character_index() -> Optional[Dict]:
    """載入同字索引"""
    config = get_config()
    index_path = config.get_index_path('character_index')

    if not os.path.exists(index_path):
        print("[Error] 同字索引不存在")
        print("請先執行「建立/更新資料索引」")
        return None

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_single_character(character: str, char_map: Dict, loader: FontDataLoader,
                            name_to_display: Dict, selected_calligraphers: Optional[List[str]] = None) -> Optional[np.ndarray]:
    """
    比對單一字元，返回合成圖片的 numpy array

    Args:
        character: 要比對的字元
        char_map: 字元索引對應表
        loader: 資料載入器
        name_to_display: 英文名稱到中文顯示名稱的對應
        selected_calligraphers: 要包含的書法家顯示名稱列表（可選，若為 None 則包含全部）

    Returns:
        合成後的圖片 array，失敗返回 None
    """
    if character not in char_map:
        print(f"  [Skip] 字元「{character}」不在索引中")
        return None

    calligraphers = char_map[character]
    num_cals = len(calligraphers)

    if num_cals < 2:
        print(f"  [Skip] 字元「{character}」只有 {num_cals} 位書法家，無法比對")
        return None

    # 載入圖片
    images = {}
    for cal_name, instances in calligraphers.items():
        display_name = name_to_display.get(cal_name, cal_name)

        # 若指定了選中的書法家，跳過未選中的
        if selected_calligraphers and display_name not in selected_calligraphers:
            continue

        if instances:
            img_path = instances[0]['image_path']
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    images[display_name] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if not images:
        print(f"  [Error] 字元「{character}」無法載入任何圖片")
        return None

    # 建立比對圖
    num_images = len(images)
    fig, axes = plt.subplots(1, num_images, figsize=(num_images * 3, 4))

    if num_images == 1:
        axes = [axes]

    fig.suptitle(f'字元比對：「{character}」', fontsize=16, fontweight='bold')

    for idx, (display_name, img) in enumerate(sorted(images.items())):
        ax = axes[idx]
        ax.imshow(img, cmap='gray')
        ax.set_title(f"{display_name}", fontsize=14, fontweight='bold')
        ax.axis('off')

    # 隱藏多餘的子圖
    for idx in range(num_images, len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()

    # 轉換為 numpy array
    fig.canvas.draw()

    # 使用 buffer_rgba() 替代 tostring_rgb()
    buf = fig.canvas.buffer_rgba()
    img_array = np.frombuffer(buf, dtype=np.uint8)
    img_array = img_array.reshape(fig.canvas.get_width_height()[::-1] + (4,))

    # 移除 alpha 通道（RGBA -> RGB）
    img_array = img_array[:, :, :3]

    plt.close(fig)

    return img_array


def batch_compare_to_images(characters: str, output_dir: str = "./output/batch", selected_calligraphers: Optional[List[str]] = None) -> List[str]:
    """
    批次比對多個字元，輸出獨立 PNG 檔案

    Args:
        characters: 要比對的字元字串（如："天地人和"）
        output_dir: 輸出目錄
        selected_calligraphers: 要包含的書法家顯示名稱列表（可選，若為 None 則包含全部）

    Returns:
        成功產生的檔案路徑列表
    """
    print("\n" + "="*70)
    print(" 批次同字比對 - PNG 模式")
    print("="*70)

    # 載入索引
    char_index = load_character_index()
    if not char_index:
        return []

    char_map = char_index.get('character_map', {})

    # 載入 display_name 對應
    loader = FontDataLoader()
    name_to_display = {cal['name']: cal['display_name'] for cal in loader.calligraphers}

    # 建立輸出目錄
    os.makedirs(output_dir, exist_ok=True)

    # 處理每個字元
    char_list = list(characters)
    total = len(char_list)
    success_files = []

    # 過濾無效字元（處理編碼問題）
    valid_char_list = [c for c in char_list if ord(c) < 0x10000]  # BMP 字元

    print(f"\n要比對的字元: {len(valid_char_list)} 個")
    print(f"總數: {total} 個字\n")

    for idx, char in enumerate(valid_char_list, 1):
        print(f"[{idx}/{total}] 處理「{char}」...", end=" ")

        img_array = compare_single_character(char, char_map, loader, name_to_display, selected_calligraphers)

        if img_array is not None:
            # 儲存圖片
            output_path = os.path.join(output_dir, f"comparison_{char}.png")
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_path, img_bgr)
            success_files.append(output_path)
            print(f"[OK] {os.path.basename(output_path)}")
        else:
            print("[Failed]")

    print("\n" + "="*70)
    print(f" 完成！成功產生 {len(success_files)}/{total} 個比對圖")
    print(f" 輸出目錄: {output_dir}")
    print("="*70 + "\n")

    return success_files


def batch_compare_to_pdf(characters: str, output_path: str = "./output/batch_comparison_report.pdf", selected_calligraphers: Optional[List[str]] = None):
    """
    批次比對多個字元，輸出單一 PDF 報告

    Args:
        characters: 要比對的字元字串（如："天地人和"）
        output_path: PDF 輸出路徑
        selected_calligraphers: 要包含的書法家顯示名稱列表（可選，若為 None 則包含全部）
    """
    try:
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError:
        print("[Error] 需要 matplotlib 的 PDF 支援")
        print("請執行: pip install matplotlib")
        return

    print("\n" + "="*70)
    print(" 批次同字比對 - PDF 模式")
    print("="*70)

    # 載入索引
    char_index = load_character_index()
    if not char_index:
        return

    char_map = char_index.get('character_map', {})

    # 載入 display_name 對應
    loader = FontDataLoader()
    name_to_display = {cal['name']: cal['display_name'] for cal in loader.calligraphers}

    # 建立輸出目錄
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 處理每個字元
    char_list = list(characters)
    total = len(char_list)
    success_count = 0

    # 過濾無效字元（處理編碼問題）
    valid_char_list = [c for c in char_list if ord(c) < 0x10000]  # BMP 字元

    print(f"\n要比對的字元: {len(valid_char_list)} 個")
    print(f"總數: {total} 個字\n")

    with PdfPages(output_path) as pdf:
        for idx, char in enumerate(valid_char_list, 1):
            print(f"[{idx}/{total}] 處理「{char}」...", end=" ")

            if char not in char_map:
                print(f"[Skip] 不在索引中")
                continue

            calligraphers = char_map[char]
            num_cals = len(calligraphers)

            if num_cals < 2:
                print(f"[Skip] 只有 {num_cals} 位書法家")
                continue

            # 載入圖片
            images = {}
            for cal_name, instances in calligraphers.items():
                display_name = name_to_display.get(cal_name, cal_name)

                # 若指定了選中的書法家，跳過未選中的
                if selected_calligraphers and display_name not in selected_calligraphers:
                    continue

                if instances:
                    img_path = instances[0]['image_path']
                    if os.path.exists(img_path):
                        img = cv2.imread(img_path)
                        if img is not None:
                            images[display_name] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            if not images:
                print("[Error] 無法載入圖片")
                continue

            # 建立比對圖（直接繪製到 PDF）
            num_images = len(images)
            fig, axes = plt.subplots(1, num_images, figsize=(num_images * 3, 4))

            if num_images == 1:
                axes = [axes]

            fig.suptitle(f'字元比對：「{char}」', fontsize=16, fontweight='bold')

            for i, (display_name, img) in enumerate(sorted(images.items())):
                ax = axes[i]
                ax.imshow(img, cmap='gray')
                ax.set_title(f"{display_name}", fontsize=14, fontweight='bold')
                ax.axis('off')

            # 隱藏多餘的子圖
            for i in range(num_images, len(axes)):
                axes[i].axis('off')

            plt.tight_layout()

            # 儲存到 PDF
            pdf.savefig(fig, dpi=150, bbox_inches='tight')
            plt.close(fig)

            success_count += 1
            print("[OK]")

    print("\n" + "="*70)
    print(f" 完成！成功產生 {success_count}/{total} 個比對圖")
    print(f" PDF 檔案: {output_path}")
    print("="*70 + "\n")


def interactive_mode():
    """互動式批次比對"""
    print("\n" + "="*70)
    print(" 批次同字比對工具")
    print("="*70)

    # 檢查索引
    char_index = load_character_index()
    if not char_index:
        return

    common_chars = char_index.get('common_characters', [])
    total_chars = len(char_index.get('character_map', {}))

    print(f"\n 可比對字數: {total_chars}")
    print(f" 共有字數: {len(common_chars)}")

    if common_chars:
        print(f"\n 共有字（前 20 個）:")
        print(f"   {''.join(common_chars[:20])}")

    print("\n" + "-"*70)

    # 輸入字元
    print("\n請輸入要比對的字元（不需空格，例如：天地人和）")
    print("或輸入「common」使用前 10 個共有字")
    characters = input("字元: ").strip()

    if not characters:
        print("[Error] 未輸入任何字元")
        return

    if characters.lower() == 'common':
        characters = ''.join(common_chars[:10])
        print(f"\n使用共有字: {characters}")

    # 選擇輸出格式
    print("\n輸出格式:")
    print("  1. 獨立 PNG 檔案（每個字一張圖）")
    print("  2. 單一 PDF 報告（所有字在一個檔案）")

    choice = input("\n請選擇 (1/2): ").strip()

    if choice == '1':
        output_dir = input("\n輸出目錄 (預設: ./output/batch): ").strip()
        if not output_dir:
            output_dir = "./output/batch"
        batch_compare_to_images(characters, output_dir)
    elif choice == '2':
        output_path = input("\n輸出檔案 (預設: ./output/batch_comparison_report.pdf): ").strip()
        if not output_path:
            output_path = "./output/batch_comparison_report.pdf"
        batch_compare_to_pdf(characters, output_path)
    else:
        print("[Error] 無效選項")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='批次同字比對工具')
    parser.add_argument('characters', nargs='?', help='要比對的字元（如：天地人和）')
    parser.add_argument('--mode', choices=['png', 'pdf'], default='png',
                       help='輸出模式：png（獨立圖片）或 pdf（單一報告）')
    parser.add_argument('--output', help='輸出路徑')
    parser.add_argument('--common', type=int, metavar='N',
                       help='使用前 N 個共有字（如：--common 10）')

    args = parser.parse_args()

    # 互動模式
    if not args.characters and not args.common:
        interactive_mode()
        sys.exit(0)

    # 命令列模式
    if args.common:
        char_index = load_character_index()
        if char_index:
            common_chars = char_index.get('common_characters', [])
            characters = ''.join(common_chars[:args.common])
            print(f"使用前 {args.common} 個共有字: {characters}")
        else:
            sys.exit(1)
    else:
        characters = args.characters

    if args.mode == 'png':
        output_dir = args.output or "./output/batch"
        batch_compare_to_images(characters, output_dir)
    else:  # pdf
        output_path = args.output or "./output/batch_comparison_report.pdf"
        batch_compare_to_pdf(characters, output_path)
