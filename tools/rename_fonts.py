#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
書法字帖圖片編號工具

功能：
1. 掃描字帖資料夾中的所有圖片
2. 如果有 XX.txt 檔案，按照檔案中的字元順序對應圖片
3. 如果沒有 XX.txt，按照原始檔名中的數字排序
4. 重新命名為 char_XXXX.png (可自訂起始編號)

使用方法：
    python rename_fonts.py <font_num> [--start <number>]
    例如: python rename_fonts.py 04 --start 100

說明：
- 會在原資料夾中創建 backup/ 子目錄來備份原始檔案
- 新編號的檔案保存在原地
"""

import os
import sys
import re
import shutil
from pathlib import Path
from collections import OrderedDict

# Windows 編碼設置
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class FontRenamer:
    def __init__(self, font_num, start_idx=1):
        """
        初始化字帖編號工具

        Args:
            font_num: 字帖編號（如 '00', '01', '02', '03', '04'）
            start_idx: 重新命名的起始編號，預設為 1
        """
        self.font_num = str(font_num).zfill(2)
        self.start_idx = start_idx
        self.project_root = Path(__file__).parent.parent
        self.font_dir = self.project_root / "Fonts" / "my_fonts" / self.font_num
        self.txt_file = self.project_root / "Fonts" / f"{self.font_num}.txt"
        self.auto_confirm = False  # 自動確認標籤

        # 驗證目錄是否存在
        if not self.font_dir.exists():
            raise FileNotFoundError(f"字帖資料夾不存在: {self.font_dir}")

        print(f"✓ 字帖資料夾: {self.font_dir}")
        print(f"✓ 字元順序檔: {self.txt_file}")
        print(f"✓ 起始編號設定為: {self.start_idx:04d}")
        print()

    def load_char_order(self):
        """
        從 XX.txt 檔案中載入字元順序

        Returns:
            list: 字元列表，如果檔案不存在則返回 None
        """
        if not self.txt_file.exists():
            print(f"⚠ 找不到字元順序檔 {self.txt_file}")
            print("  將按照原始檔名號碼順序進行編號\n")
            return None

        try:
            with open(self.txt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 按行分割，每行是一個字
            chars = [line.strip() for line in content.split('\n') if line.strip()]

            print(f"✓ 已載入 {len(chars)} 個字元順序")
            print(f"  首字: {chars[0]}, 末字: {chars[-1]}\n")

            return chars
        except Exception as e:
            print(f"✗ 讀取字元順序檔失敗: {e}")
            print("  將按照原始檔名號碼順序進行編號\n")
            return None

    def get_image_files(self):
        """
        掃描資料夾中的所有圖片檔案

        Returns:
            list: 圖片檔案路徑列表
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
        images = []

        for file_path in sorted(self.font_dir.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                images.append(file_path)

        print(f"✓ 找到 {len(images)} 個圖片檔案")
        return images

    def extract_number(self, filename):
        """
        從檔名中提取數字

        Args:
            filename: 檔案名稱

        Returns:
            int: 提取到的數字，沒有數字則返回 0
        """
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else 0

    def sort_images_by_number(self, images):
        """
        按原始檔名中的數字排序圖片

        Args:
            images: 圖片檔案路徑列表

        Returns:
            list: 排序後的圖片列表
        """
        return sorted(images, key=lambda x: self.extract_number(x.name))

    def sort_images_by_chars(self, images, chars):
        """
        按字元順序排序圖片

        需要 OCR GUI 工具來對應原始檔案和字元

        Args:
            images: 圖片檔案路徑列表
            chars: 字元列表

        Returns:
            list: 排序後的圖片列表
        """
        if len(chars) != len(images):
            print(f"⚠ 警告: 字元數({len(chars)}) ≠ 圖片數({len(images)})")
            print("  請使用 OCR 審查工具手動對應，或編輯 .txt 檔案")
            print("  執行指令: python tools/2_ocr_reviewer_gui.py\n")
            return None

        # 簡單對應：假設原始檔案已按順序排列
        sorted_images = self.sort_images_by_number(images)

        print(f"✓ 已按 {self.txt_file.name} 的字元順序關聯圖片")
        return sorted_images

    def backup_files(self, images):
        """
        備份原始檔案

        Args:
            images: 圖片檔案路徑列表
        """
        backup_dir = self.font_dir / "backup"

        if backup_dir.exists():
            print(f"✓ 備份目錄已存在: {backup_dir}")
            return

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)

            for image in images:
                shutil.copy2(image, backup_dir / image.name)

            print(f"✓ 已備份 {len(images)} 個原始檔案到: {backup_dir}\n")
        except Exception as e:
            print(f"✗ 備份失敗: {e}")
            raise

    def rename_files(self, images):
        """
        重新命名檔案為 char_XXXX.png

        Args:
            images: 圖片檔案路徑列表（已排序）
        """
        print(f"開始重新命名 {len(images)} 個檔案...\n")

        renamed_count = 0
        errors = []

        # 重點修改處：使用 self.start_idx 替代原來的 1
        for idx, old_path in enumerate(images, self.start_idx):
            # 生成新的檔案名
            new_name = f"char_{idx:04d}.png"
            new_path = self.font_dir / new_name

            try:
                # 如果已存在相同名稱，先刪除
                if new_path.exists() and new_path != old_path:
                    new_path.unlink()

                # 重新命名
                old_path.rename(new_path)
                renamed_count += 1

                # 每 50 個檔案顯示一次進度
                if renamed_count % 50 == 0:
                    print(f"  進度: {renamed_count}/{len(images)}")

            except Exception as e:
                errors.append(f"  ✗ {old_path.name} → {new_name}: {e}")

        print()
        print(f"✓ 成功重新命名 {renamed_count} 個檔案")

        if errors:
            print(f"\n✗ 出錯 {len(errors)} 個:")
            for error in errors:
                print(error)
            return False

        return True

    def run(self):
        """
        執行完整的編號流程
        """
        print(f"{'='*60}")
        print(f"  書法字帖編號工具 - 字帖 {self.font_num}")
        print(f"{'='*60}\n")

        try:
            # 第 1 步：載入字元順序
            chars = self.load_char_order()

            # 第 2 步：掃描圖片
            images = self.get_image_files()
            if not images:
                print("✗ 找不到圖片檔案！")
                return False
            print()

            # 第 3 步：根據有無 .txt 檔案決定排序方式
            if chars:
                # 按字元順序排序
                sorted_images = self.sort_images_by_chars(images, chars)
                if sorted_images is None:
                    print("✗ 字元數與圖片數不匹配，請先解決")
                    return False
            else:
                # 按原始檔名號碼排序
                sorted_images = self.sort_images_by_number(images)
                print(f"✓ 已按原始檔名號碼順序排序\n")

            # 第 4 步：備份原始檔案
            if self.auto_confirm:
                print("將建立備份並重新命名檔案...")
            else:
                confirm = input("將建立備份並重新命名檔案，確認繼續? (y/n): ").lower()
                if confirm != 'y':
                    print("已取消操作")
                    return False

            print()
            self.backup_files(sorted_images)

            # 第 5 步：重新命名
            success = self.rename_files(sorted_images)

            if success:
                print(f"\n{'='*60}")
                print(f"  ✓ 字帖 {self.font_num} 編號完成！")
                print(f"  新檔案: {self.font_dir}")
                print(f"  備份目錄: {self.font_dir / 'backup'}")
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
        print("  python rename_fonts.py <font_num> [--yes] [--start <number>]")
        print("\n範例:")
        print("  python rename_fonts.py 00                # 從 0001 開始（需要互動確認）")
        print("  python rename_fonts.py 04 --yes          # 從 0001 開始（自動確認）")
        print("  python rename_fonts.py 01 --start 500    # 從 char_0500.png 開始")
        print("  python rename_fonts.py 02 -y --start 150 # 結合多個參數使用")
        sys.exit(1)

    font_num = sys.argv[1]
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    
    # 解析自訂的起始編號
    start_idx = 1
    if '--start' in sys.argv:
        try:
            start_index_pos = sys.argv.index('--start')
            start_idx = int(sys.argv[start_index_pos + 1])
        except (ValueError, IndexError):
            print("\n✗ 錯誤：--start 後面必須接有效的數字 (例如: --start 100)")
            sys.exit(1)

    try:
        # 將 start_idx 傳入初始化
        renamer = FontRenamer(font_num, start_idx=start_idx)
        renamer.auto_confirm = auto_confirm
        success = renamer.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 初始化失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()