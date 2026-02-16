"""
書法 FFT 分析系統 - 主程式
統一入口，整合所有功能模組
"""
import os
import sys

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(__file__))

from src.utils import get_config


def print_header():
    """列印程式標題"""
    print("\n" + "="*70)
    print(" 書法 FFT 分析系統 v2.0")
    print(" 使用傅立葉描述子分析書法風格")
    print("="*70)


def print_menu():
    """列印主選單"""
    print("\n" + "-"*70)
    print(" 功能選單:")
    print("-"*70)
    print("  1. 建立/更新資料索引")
    print("  2. 執行 FFT 風格分析")
    print("  3. 同字比對器（互動模式）")
    print("  4. 批次同字比對")
    print("  5. 查看索引統計")
    print("  6. 預處理工具選單")
    print("  0. 離開")
    print("-"*70)


def build_index():
    """建立/更新資料索引"""
    print("\n[INFO] 啟動索引建立工具...")
    from tools.analysis import build_index as idx_builder
    idx_builder.build_fonts_index()
    idx_builder.build_character_index()


def run_fft_analysis():
    """執行 FFT 風格分析"""
    print("\n" + "="*70)
    print(" FFT 風格分析設定")
    print("="*70)

    try:
        sample_input = input("\n請輸入樣本數（預設 30，全部請輸入 all）: ").strip()

        if sample_input.lower() == 'all':
            max_samples = None
            print("[INFO] 將處理所有圖片")
        elif sample_input == '':
            max_samples = 30
            print("[INFO] 使用預設樣本數: 30")
        else:
            max_samples = int(sample_input)
            print(f"[INFO] 設定樣本數: {max_samples}")
    except ValueError:
        print("[Warning] 無效輸入，使用預設值 30")
        max_samples = 30

    print("\n[INFO] 啟動 FFT 分析...")
    from analyze_styles import run_style_analysis
    run_style_analysis(max_samples=max_samples)


def character_comparator():
    """同字比對器（互動模式）"""
    print("\n[INFO] 啟動同字比對器...")
    from character_comparator import interactive_mode
    interactive_mode()


def batch_character_comparison():
    """批次同字比對"""
    print("\n[INFO] 啟動批次同字比對工具...")
    from tools.analysis.batch_comparator import interactive_mode
    interactive_mode()


def view_index_statistics():
    """查看索引統計"""
    from pathlib import Path
    import json

    config = get_config()
    fonts_index_path = config.get_index_path('fonts_index')
    char_index_path = config.get_index_path('character_index')

    print("\n" + "="*70)
    print(" 索引統計資訊")
    print("="*70)

    # 檢查索引檔案是否存在
    if not os.path.exists(fonts_index_path):
        print("\n[Error] 字庫索引不存在")
        print(f"請先執行選項 1（建立索引）")
        print("\n按 Enter 返回主選單...")
        input()
        return

    # 載入索引
    with open(fonts_index_path, 'r', encoding='utf-8') as f:
        fonts_index = json.load(f)

    with open(char_index_path, 'r', encoding='utf-8') as f:
        char_index = json.load(f)

    # 顯示統計
    print(f"\n 字庫總覽:")
    print(f"  - 書法家數量: {fonts_index['total_calligraphers']}")

    total_images = 0
    for name, info in fonts_index['calligraphers'].items():
        total_images += info['total_images']
        print(f"\n  【{info['display_name']}】({info['dynasty']} - {info['style']})")
        print(f"    圖片數: {info['total_images']}")
        print(f"    獨特字: {info['unique_characters']}")

    print(f"\n 總計: {total_images} 張圖片")

    print(f"\n 同字索引:")
    print(f"  - 總獨特字數: {char_index['total_unique_characters']}")
    print(f"  - 所有書法家共有: {char_index['total_common_characters']} 個字")
    print(f"  - 可比對字數: {len(char_index['character_map'])} 個")

    if char_index['common_characters']:
        print(f"\n  前 30 個共有字:")
        for i in range(0, min(30, len(char_index['common_characters'])), 10):
            print(f"    {''.join(char_index['common_characters'][i:i+10])}")

    print("\n" + "="*70)
    print("\n按 Enter 返回主選單...")
    input()


def preprocessing_menu():
    """預處理工具選單"""
    while True:
        print("\n" + "="*70)
        print(" 預處理工具選單")
        print("="*70)
        print("\n可用工具:")
        print("  1. 紅框檢測與浮水印移除 (crop_and_denoise.py)")
        print("  2. 網格式字元切割 (grid_splitter.py)")
        print("  3. 浮水印移除 (watermark_remover.py)")
        print("  4. 完整預處理流程 (full_pipeline.py)")
        print("  5. 人工修補序列 (manual_patcher.py)")
        print("  0. 返回主選單")
        print("-"*70)

        choice = input("\n請選擇功能: ").strip()

        if choice == '0':
            break
        elif choice in ['1', '2', '3', '4', '5']:
            print("\n[Info] 預處理工具需要在命令列獨立執行")
            print("請參考 tools/preprocessing/README.md 了解使用方式")
            print("\n按 Enter 繼續...")
            input()
        else:
            print("[Error] 無效選項")


def main():
    """主程式"""
    print_header()

    # 檢查配置檔
    config = get_config()

    while True:
        print_menu()
        choice = input("\n請選擇功能 (0-6): ").strip()

        try:
            if choice == '0':
                print("\n感謝使用！再見！\n")
                break

            elif choice == '1':
                build_index()
                print("\n按 Enter 返回主選單...")
                input()

            elif choice == '2':
                run_fft_analysis()
                print("\n按 Enter 返回主選單...")
                input()

            elif choice == '3':
                character_comparator()

            elif choice == '4':
                batch_character_comparison()

            elif choice == '5':
                view_index_statistics()

            elif choice == '6':
                preprocessing_menu()

            else:
                print("[Error] 無效選項，請輸入 0-6")

        except KeyboardInterrupt:
            print("\n\n程式中斷。再見！\n")
            break

        except Exception as e:
            print(f"\n[Error] 發生錯誤: {e}")
            print("按 Enter 返回主選單...")
            input()


if __name__ == "__main__":
    main()
