#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字帖 CSV 檔案生成工具

功能：
根據 XX.txt 檔案生成對應的 XX.csv 檔案
CSV 檔案用於存儲圖片檔名、字元、識別信度等資訊

使用方法：
    python generate_font_csv.py <font_num>
    例如: python generate_font_csv.py 04

說明：
- XX.txt 應該包含每行一個字元的字元序列
- 圖片應該已經按 char_0001.png, char_0002.png, ... char_XXXX.png 命名
- 生成的 CSV 放在 Fonts/my_fonts/csv/ 目錄下
"""

import os
import sys
import csv
from pathlib import Path

# Windows 編碼設置
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class FontCSVGenerator:
    def __init__(self, font_num):
        """
        初始化 CSV 生成工具

        Args:
            font_num: 字帖編號（如 '04'）
        """
        self.font_num = str(font_num).zfill(2)
        self.project_root = Path(__file__).parent.parent
        self.font_dir = self.project_root / "Fonts" / "my_fonts" / self.font_num
        # 優先讀 docs/XX.txt（一字一行格式），不存在才退回 Fonts/XX.txt
        docs_txt = self.project_root / "docs" / f"{self.font_num}.txt"
        fonts_txt = self.project_root / "Fonts" / f"{self.font_num}.txt"
        self.txt_file = docs_txt if docs_txt.exists() else fonts_txt
        self.csv_dir = self.project_root / "Fonts" / "my_fonts" / "csv"
        self.csv_file = self.csv_dir / f"{self.font_num}.csv"
        self.auto_confirm = False  # 自動確認標籤

        # 驗證檔案和目錄
        if not self.font_dir.exists():
            raise FileNotFoundError(f"字帖資料夾不存在: {self.font_dir}")
        if not self.txt_file.exists():
            raise FileNotFoundError(f"字元順序檔不存在（找過 docs/{self.font_num}.txt 和 Fonts/{self.font_num}.txt）")

        # 建立 csv 目錄
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        print(f"✓ 字帖資料夾: {self.font_dir}")
        print(f"✓ 字元順序檔: {self.txt_file}")
        print(f"✓ CSV 輸出目錄: {self.csv_dir}")
        print()

    def load_characters(self):
        """
        從 XX.txt 檔案中載入字元

        Returns:
            list: 字元列表
        """
        try:
            with open(self.txt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 按行分割，每行是一個字
            chars = [line.strip() for line in content.split('\n') if line.strip()]

            print(f"✓ 已載入 {len(chars)} 個字元")
            if chars:
                print(f"  首字: {chars[0]}, 末字: {chars[-1]}")
            print()

            return chars
        except Exception as e:
            print(f"✗ 讀取字元順序檔失敗: {e}")
            raise

    def get_image_count(self):
        """
        掃描資料夾中的圖片數量

        Returns:
            int: 圖片檔案數量
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
        count = 0

        for file_path in self.font_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                count += 1

        print(f"✓ 找到 {count} 個圖片檔案")
        return count

    def generate_csv(self, characters):
        """
        生成 CSV 檔案

        Args:
            characters: 字元列表
        """
        image_count = self.get_image_count()

        # 檢查字元數是否與圖片數相符
        if len(characters) != image_count:
            print(f"\n⚠ 警告: 字元數({len(characters)}) ≠ 圖片數({image_count})")
            if not self.auto_confirm:
                response = input("是否繼續生成? (y/n): ").lower()
                if response != 'y':
                    print("已取消")
                    return False
            else:
                print("(自動確認繼續生成)")
        else:
            print(f"✓ 字元數與圖片數相符 ({len(characters)})")

        print(f"\n生成 CSV 檔案: {self.csv_file}")

        try:
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # 寫入表頭
                writer.writerow(['filename', 'character', 'confidence'])

                # 寫入每一行
                for idx, character in enumerate(characters, 1):
                    filename = f"char_{idx:04d}.png"
                    confidence = 1.0000  # 預設信度（用戶已驗證）
                    writer.writerow([filename, character, f"{confidence:.4f}"])

            print(f"✓ 已成功生成 {len(characters)} 行 CSV 檔案")
            print(f"  檔案位置: {self.csv_file}")
            return True

        except Exception as e:
            print(f"✗ 生成 CSV 失敗: {e}")
            return False

    def run(self):
        """
        執行完整的 CSV 生成流程
        """
        print(f"{'='*60}")
        print(f"  字帖 CSV 檔案生成工具 - 字帖 {self.font_num}")
        print(f"{'='*60}\n")

        try:
            # 載入字元
            characters = self.load_characters()

            # 驗證圖片數量
            image_count = self.get_image_count()
            print()

            # 生成 CSV
            success = self.generate_csv(characters)

            if success:
                print(f"\n{'='*60}")
                print(f"  ✓ 字帖 {self.font_num} CSV 檔案生成完成！")
                print(f"{'='*60}")

            return success

        except Exception as e:
            print(f"\n✗ 發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python generate_font_csv.py <font_num> [--yes]")
        print("\n範例:")
        print("  python generate_font_csv.py 04         # 生成 04.csv（需要互動確認）")
        print("  python generate_font_csv.py 04 --yes   # 生成 04.csv（自動確認）")
        sys.exit(1)

    font_num = sys.argv[1]
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    try:
        generator = FontCSVGenerator(font_num)
        generator.auto_confirm = auto_confirm
        success = generator.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 初始化失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
