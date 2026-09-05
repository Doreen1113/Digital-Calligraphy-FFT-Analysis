"""
build_pairs.py
為 zi2zi / pix2pix 風格轉換訓練建立配對資料集。

輸出結構：
  data/paired/
    source/          ← 標楷體渲染（所有字共用，256×256 白底黑字）
      {unicode_hex}.png
    target/
      zhiyong_00/    ← 每位書法家各一個資料夾
        {unicode_hex}_{filename}.png
      ouyang_xun_03/
        ...
    pairs/           ← zi2zi 格式：512×256（左=標準，右=書法）
      zhiyong_00/
        {unicode_hex}_{filename}.png
      ...

用法：
  python tools/build_pairs.py
  python tools/build_pairs.py --cal zhiyong_00      # 只處理某書法家
  python tools/build_pairs.py --size 256            # 輸出尺寸（預設 256）
  python tools/build_pairs.py --no-pairs            # 只生 source/target，不生 pairs
"""

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── 路徑設定 ─────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
CHAR_INDEX = ROOT / "data" / "index" / "character_index.json"
OUT_DIR    = ROOT / "data" / "paired"
FONT_PATH  = Path(r"C:\Windows\Fonts\kaiu.ttf")   # 標楷體

# ── 影像處理 ──────────────────────────────────────────────────────────────────

def render_standard(char: str, size: int = 256) -> np.ndarray:
    """用標楷體把字渲染成 size×size 白底黑字 numpy array（uint8）。"""
    img = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(img)

    font_size = int(size * 0.80)
    try:
        font = ImageFont.truetype(str(FONT_PATH), font_size)
    except OSError:
        raise RuntimeError(f"找不到字型檔：{FONT_PATH}")

    # 置中
    bbox = draw.textbbox((0, 0), char, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    draw.text((x, y), char, fill=0, font=font)

    return np.array(img)


def load_calligraphy(img_path: str, size: int = 256) -> np.ndarray | None:
    """載入書法圖片並轉成 size×size 白底黑字 uint8 array。"""
    p = Path(img_path.replace("\\", "/"))
    if not p.exists():
        # 嘗試從專案根目錄找相對路徑
        rel = str(p).split("Fonts/my_fonts/")[-1] if "Fonts/my_fonts/" in str(p) else None
        if rel:
            p = ROOT / "Fonts" / "my_fonts" / rel
        if not p.exists():
            return None

    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    # 確保白底黑字
    edge = np.concatenate([img[0, :], img[-1, :], img[:, 0], img[:, -1]])
    if np.mean(edge) < 127:
        img = 255 - img

    img = cv2.medianBlur(img, 3)
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    return img


def make_pair(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """拼成 zi2zi 格式：(size × size*2)，左=標準，右=書法。"""
    return np.concatenate([source, target], axis=1)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def build(cal_filter: str | None, size: int, make_pairs: bool):
    print(f"[build_pairs] 讀取索引：{CHAR_INDEX}")
    with open(CHAR_INDEX, encoding="utf-8") as f:
        index = json.load(f)

    char_map = index.get("character_map", {})
    calligraphers = index.get("calligraphers", [])
    print(f"  字元數：{len(char_map)}　書法家：{calligraphers}")

    if cal_filter:
        calligraphers = [c for c in calligraphers if c == cal_filter]
        if not calligraphers:
            sys.exit(f"找不到書法家：{cal_filter}")

    # 建立輸出目錄
    src_dir = OUT_DIR / "source"
    src_dir.mkdir(parents=True, exist_ok=True)
    for cal in calligraphers:
        (OUT_DIR / "target" / cal).mkdir(parents=True, exist_ok=True)
        if make_pairs:
            (OUT_DIR / "pairs" / cal).mkdir(parents=True, exist_ok=True)

    stats = {cal: {"ok": 0, "skip": 0} for cal in calligraphers}
    src_cache: dict[str, np.ndarray] = {}   # 同一個字只渲染一次

    total_chars = len(char_map)
    for ci, (char, cal_data) in enumerate(char_map.items()):
        if (ci + 1) % 100 == 0:
            print(f"  進度 {ci+1}/{total_chars}…")

        # 渲染標準字型（cache）
        if char not in src_cache:
            try:
                src_img = render_standard(char, size)
                src_cache[char] = src_img
                # 儲存 source（unicode hex 命名，避免檔名非法字元）
                hex_name = f"{ord(char):05X}.png"
                cv2.imwrite(str(src_dir / hex_name), src_img)
            except Exception as e:
                print(f"  [!] 渲染失敗 '{char}': {e}")
                src_cache[char] = None
                continue

        src_img = src_cache[char]
        if src_img is None:
            continue

        hex_name = f"{ord(char):05X}"

        for cal in calligraphers:
            if cal not in cal_data:
                continue
            instances = cal_data[cal]
            if not instances:
                continue

            for inst in instances:
                img_path = inst.get("image_path", "")
                orig_filename = Path(img_path).stem   # e.g. char_0001
                tgt_img = load_calligraphy(img_path, size)

                if tgt_img is None:
                    stats[cal]["skip"] += 1
                    continue

                out_name = f"{hex_name}_{orig_filename}.png"

                # target
                cv2.imwrite(str(OUT_DIR / "target" / cal / out_name), tgt_img)

                # pair（zi2zi 格式）
                if make_pairs:
                    pair = make_pair(src_img, tgt_img)
                    cv2.imwrite(str(OUT_DIR / "pairs" / cal / out_name), pair)

                stats[cal]["ok"] += 1

    print("\n[build_pairs] 完成！")
    print(f"{'書法家':<20} {'成功':>6} {'略過':>6}")
    print("-" * 36)
    for cal, s in stats.items():
        print(f"{cal:<20} {s['ok']:>6} {s['skip']:>6}")
    print(f"\n輸出目錄：{OUT_DIR}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="建立書法配對訓練資料集")
    parser.add_argument("--cal",      default=None,  help="只處理指定書法家 ID")
    parser.add_argument("--size",     type=int, default=256, help="輸出圖片尺寸（預設 256）")
    parser.add_argument("--no-pairs", action="store_true",   help="不生成 pairs/ 目錄")
    args = parser.parse_args()

    build(
        cal_filter=args.cal,
        size=args.size,
        make_pairs=not args.no_pairs,
    )
