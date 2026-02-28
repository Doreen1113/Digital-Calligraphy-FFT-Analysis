"""
rename_files.py
依原檔名中的數字排序，將資料夾中的圖片重新命名為 char_XXXX.png 格式。
可自訂起始編號。支援多級編號排序（例如 0207-1, 0207-2）。
使用兩階段重新命名避免檔名衝突。

用法:
    python rename_files.py <資料夾路徑> [起始編號]

範例:
    python rename_files.py "C:/My_Project/Fourier_drawing/Fonts/temp/08" 1
"""

import os
import re
import sys
import uuid


def get_numbers_from_filename(filename: str) -> tuple:
    """從檔名中擷取所有數字並轉為整數 tuple，用於多級排序。例如 0207-1 -> (207, 1)"""
    numbers = re.findall(r"\d+", filename)
    return tuple(int(n) for n in numbers) if numbers else (-1,)


def preview_rename(folder: str, start: int) -> list[tuple[str, str]]:
    """產生 (舊檔名, 新檔名) 的預覽清單，但不實際重新命名。"""
    supported_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and os.path.splitext(f)[1].lower() in supported_exts
    ]

    if not files:
        print("找不到支援的圖片檔案。")
        return []

    # 依原始編號排序
    files.sort(key=lambda f: get_numbers_from_filename(f))

    plan = []
    for i, filename in enumerate(files):
        new_name = f"char_{start + i:04d}.png"
        plan.append((filename, new_name))

    return plan


def rename_files(folder: str, start: int, dry_run: bool = False) -> None:
    plan = preview_rename(folder, start)
    if not plan:
        return

    # 顯示預覽
    print(f"\n{'模擬模式 (Dry Run)' if dry_run else '即將執行重新命名'}")
    print(f"{'舊檔名':<35} -> 新檔名")
    print("-" * 55)
    for old, new in plan:
        print(f"  {old:<33} -> {new}")

    if dry_run:
        print(f"\n共 {len(plan)} 個檔案，模擬完成（未實際更改）。")
        return

    # 確認
    print(f"\n共 {len(plan)} 個檔案，起始編號 {start:04d}，結束編號 {start + len(plan) - 1:04d}。")
    confirm = input("確認執行？(y/N): ").strip().lower()
    if confirm != "y":
        print("已取消。")
        return

    # ================= 核心修改：兩階段重新命名 =================
    temp_plan = []
    errors = []

    # 階段 1：先全部加上隨機前綴，避免與原本的檔案撞名
    for old, new in plan:
        if old == new:
            continue # 檔名本來就對的，不用動
            
        temp_name = f"__temp_{uuid.uuid4().hex[:8]}_{new}"
        old_path = os.path.join(folder, old)
        temp_path = os.path.join(folder, temp_name)
        
        try:
            os.rename(old_path, temp_path)
            # 記錄：(暫時路徑, 最終目標路徑, 原始檔名)
            temp_plan.append((temp_path, os.path.join(folder, new), old))
        except OSError as e:
            errors.append(f"  階段 1 失敗 (無法重命名為暫存檔) {old}: {e}")

    # 階段 2：把暫時的檔名改成最終的目標檔名
    for temp_path, new_path, old_name in temp_plan:
        try:
            # 這裡再檢查一次目標是否存在，確保萬無一失
            if os.path.exists(new_path):
                errors.append(f"  目標已存在，跳過: {os.path.basename(new_path)}")
                continue
            os.rename(temp_path, new_path)
        except OSError as e:
            errors.append(f"  階段 2 失敗 (無法重命名為最終檔) {old_name}: {e}")
    # ============================================================

    success = len(plan) - len(errors)
    print(f"\n完成！成功 {success} 個，失敗 {len(errors)} 個。")
    if errors:
        print("錯誤清單：")
        for e in errors:
            print(e)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    folder = sys.argv[1].strip().strip('"')
    start = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
    dry_run = "--dry-run" in sys.argv

    if not os.path.isdir(folder):
        print(f"錯誤：找不到資料夾 '{folder}'")
        sys.exit(1)

    if start < 1:
        print("錯誤：起始編號必須 >= 1")
        sys.exit(1)

    rename_files(folder, start, dry_run=dry_run)


if __name__ == "__main__":
    main()