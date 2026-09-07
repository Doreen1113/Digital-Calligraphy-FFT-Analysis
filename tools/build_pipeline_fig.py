"""繪製 project page 的方法流程圖（含真實書法影像，輸出 PNG）。

取代原本純文字方框的 SVG：上排是「分析」路線（原始字 → 前處理 → 低通濾波序列
→ 準確率飽和），下排是「生成」路線（標準字＋風格參考 → 模型 → 生成結果 vs 真跡）。

用法：python tools/build_pipeline_fig.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
FONT_TC = "/home/intern_2603055/projects/tuijian/fonts/edukai/edukai-5.0.ttf"

S = 2                      # 2 倍解析度，縮圖後邊緣才銳利
BG = (255, 255, 255)
INK = (26, 26, 26)
MUTED = (120, 114, 108)
LINE = (214, 210, 204)
ACCENT = (140, 47, 34)
GREEN = (31, 122, 77)

TH = 150 * S               # 縮圖尺寸
GAP = 26 * S


def load(path: Path, size: int = TH) -> Image.Image:
    im = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
    return im.convert("RGB")


def arrow(d: ImageDraw.ImageDraw, x1, y, x2, color=(150, 145, 140)):
    d.line([x1, y, x2 - 7 * S, y], fill=color, width=max(1, S))
    d.polygon([(x2, y), (x2 - 9 * S, y - 5 * S), (x2 - 9 * S, y + 5 * S)], fill=color)


def cell(canvas, d, im, x, y, caption, f_cap, color=MUTED, box=True):
    canvas.paste(im, (x, y))
    if box:
        d.rectangle([x, y, x + im.width, y + im.height], outline=LINE, width=max(1, S))
    tw = d.textlength(caption, font=f_cap)
    d.text((x + (im.width - tw) / 2, y + im.height + 8 * S), caption, font=f_cap, fill=color)


def main(out: Path):
    f_head = ImageFont.truetype(FONT_TC, 30 * S)
    f_cap = ImageFont.truetype(FONT_TC, 21 * S)
    f_note = ImageFont.truetype(FONT_TC, 20 * S)
    f_big = ImageFont.truetype(FONT_TC, 34 * S)

    lp = ROOT / "docs" / "img" / "lowpass"
    raw = load(lp / "yan_jing_100.png")
    lp02 = load(lp / "yan_jing_002.png")
    lp05 = load(lp / "yan_jing_005.png")
    lp10 = load(lp / "yan_jing_010.png")

    # 「道」的完整對照：標楷體 → 生成 → 顏真卿真跡（由 tools 事先透過平台 API 取得）
    A = Path("/tmp/pipe_assets")
    std = load(ROOT / "data" / "paired" / "source" / "09053.png")
    ref = load(A / "ref.png")
    gen = load(A / "gen.png")
    real = load(A / "real.png")

    W = 1560 * S
    H = 760 * S
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)

    M = 46 * S

    # ── 上排：分析 ──────────────────────────────────────────
    y0 = 92 * S
    d.text((M, 40 * S), "分析：風格訊號住在哪個頻段", font=f_head, fill=INK)
    d.line([M, 78 * S, W - M, 78 * S], fill=LINE, width=max(1, S))

    # 低通濾波序列，每格直接標出對應的辨識準確率（對應表 3）
    x = M
    seq = ((lp02, "保留 2%", "48.5%", MUTED), (lp05, "5%", "78.2%", MUTED),
           (lp10, "10%", "94.7%", ACCENT), (raw, "完整頻譜", "98.7%", MUTED))
    for img, lbl, acc, col in seq:
        cell(canvas, d, img, x, y0, lbl, f_cap)
        tw = d.textlength(acc, font=f_head)
        d.text((x + (TH - tw) / 2, y0 + TH + 40 * S), acc, font=f_head, fill=col)
        x += TH + 22 * S
    d.text((M, y0 + TH + 92 * S),
           "對字圖施加徑向低通濾波後重新訓練分類器：只留最低 10% 的空間頻率（已無任何筆鋒細節），"
           "辨識準確率仍有 94.7%。",
           font=f_note, fill=MUTED)

    x += 10 * S
    arrow(d, x - 16 * S, y0 + TH // 2, x + 40 * S)
    x += 58 * S
    d.text((x, y0 + TH // 2 - 46 * S), "身份訊號", font=f_head, fill=INK)
    d.text((x, y0 + TH // 2 + 6 * S), "集中在低頻結構\n而非筆鋒細節", font=f_note, fill=MUTED)

    # ── 下排：生成 ──────────────────────────────────────────
    y1 = 452 * S
    d.text((M, 400 * S), "生成：把同一個理解用到補字上", font=f_head, fill=INK)
    d.line([M, 438 * S, W - M, 438 * S], fill=LINE, width=max(1, S))

    x = M
    cell(canvas, d, std, x, y1, "標準字（內容）", f_cap)
    x += TH + 12 * S
    cell(canvas, d, ref, x, y1, "風格參考（真跡）", f_cap)
    x += TH + GAP
    arrow(d, x - GAP + 5 * S, y1 + TH // 2, x - 6 * S)

    # 模型方塊
    bw, bh = 210 * S, TH
    d.rectangle([x, y1, x + bw, y1 + bh], outline=ACCENT, width=max(1, S))
    d.text((x + 26 * S, y1 + 40 * S), "擴散模型", font=f_cap, fill=ACCENT)
    d.text((x + 26 * S, y1 + 78 * S), "本資料集微調", font=f_note, fill=MUTED)
    x += bw + GAP
    arrow(d, x - GAP + 5 * S, y1 + TH // 2, x - 6 * S)

    cell(canvas, d, gen, x, y1, "生成結果", f_cap, color=ACCENT)
    x += TH + 12 * S
    cell(canvas, d, real, x, y1, "該書法家真跡", f_cap, color=GREEN)

    x += TH + 34 * S
    d.text((x, y1 + TH // 2 - 44 * S), "34.3%", font=f_big, fill=ACCENT)
    d.text((x, y1 + TH // 2 + 4 * S), "風格辨識率\n官方權重 20.0%", font=f_note, fill=MUTED)

    d.text((M, 700 * S),
           "核心發現「身份訊號集中於低頻」貫穿兩端：決定平台診斷回饋的優先順序，也定義生成任務的損失設計。",
           font=f_note, fill=MUTED)

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.resize((W // S, H // S), Image.LANCZOS).save(out, optimize=True)
    print(f"完成 → {out}（{out.stat().st_size/1e3:.0f} KB）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/img/fig_pipeline.png")
    main(Path(ap.parse_args().out))
