"""Project page 的定性視覺素材。

1. same_char_grid.png — 同一個字 × 7 位書法家（資料集獨門結構的視覺證明），
   多列（每列一個字），乾淨白底。
2. gen_qualitative.png — 生成定性對比：標楷體 content｜style 參考｜zero-shot 生成｜真跡 GT，
   每列一位書法家。
"""
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties

import sys
sys.path.insert(0, str(Path(__file__).parent))
from features import binarize

ROOT = Path(__file__).parent.parent
FIG = Path(__file__).parent / "figures"
CJK = FontProperties(fname="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf")

DISPLAY = {"zhiyong": "智永", "ouyang_xun": "歐陽詢", "yu_shinan": "虞世南",
           "yan_zhenqing": "顏真卿", "liu_gongquan": "柳公權",
           "zhao_mengfu": "趙孟頫", "shen_yinmo": "沈尹默"}
ORDER = ["zhiyong", "ouyang_xun", "yu_shinan", "yan_zhenqing",
         "liu_gongquan", "zhao_mengfu", "shen_yinmo"]   # 依年代


def load_norm(path, size=200):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    ink = binarize(img)
    return 255 - cv2.resize(ink, (size, size), interpolation=cv2.INTER_AREA)


def same_char_grid(chars=("道", "人", "月", "學")):
    m = pd.read_csv(Path(__file__).parent / "manifest.csv")
    fig, axes = plt.subplots(len(chars), len(ORDER), figsize=(1.55 * len(ORDER), 1.72 * len(chars)))
    for i, ch in enumerate(chars):
        sub = m[m["char"] == ch]
        for j, lab in enumerate(ORDER):
            ax = axes[i, j]
            ax.axis("off")
            rows = sub[sub["label"] == lab]
            if len(rows):
                ax.imshow(load_norm(ROOT / rows.iloc[0]["path"]), cmap="gray", vmin=0, vmax=255)
            else:
                ax.text(0.5, 0.5, "—", ha="center", va="center", fontsize=18, color="#bbb")
            if i == 0:
                ax.set_title(DISPLAY[lab], fontsize=13, fontproperties=CJK, pad=8)
    fig.tight_layout()
    fig.savefig(FIG / "same_char_grid.png", dpi=150, bbox_inches="tight", facecolor="white")
    print("saved same_char_grid.png")


def gen_qualitative(n_rows=5):
    gm = pd.read_csv(Path(__file__).parent / "generated" / "generation_manifest.csv")
    # 每位書法家挑一列，優先挑筆畫適中的
    picks = gm.groupby("cal").nth(3).reset_index() if hasattr(gm.groupby("cal"), "nth") else gm
    picks = gm.groupby("cal").head(4).groupby("cal").tail(1).head(n_rows)
    cols = ["content", "style", "gen", "gt"]
    titles = ["標準字", "風格參考", "生成結果", "書法家真跡"]
    fig, axes = plt.subplots(len(picks), 4, figsize=(1.75 * 4, 1.9 * len(picks)))
    for i, (_, r) in enumerate(picks.iterrows()):
        for j, c in enumerate(cols):
            ax = axes[i, j]
            ax.axis("off")
            ax.imshow(load_norm(Path(r[c]) if str(r[c]).startswith("/") else ROOT / r[c]),
                      cmap="gray", vmin=0, vmax=255)
            if i == 0:
                ax.set_title(titles[j], fontsize=11, fontproperties=CJK, pad=8)
        cal_label = DISPLAY[r["cal"].rsplit("_", 1)[0] if r["cal"].rsplit("_", 1)[0] in DISPLAY
                            else "_".join(r["cal"].split("_")[:-1])]
        axes[i, 0].text(-0.14, 0.5, cal_label, transform=axes[i, 0].transAxes,
                        rotation=90, va="center", ha="center", fontsize=12, fontproperties=CJK)
    fig.tight_layout()
    fig.savefig(FIG / "gen_qualitative.png", dpi=150, bbox_inches="tight", facecolor="white")
    print("saved gen_qualitative.png")


if __name__ == "__main__":
    same_char_grid()
    gen_qualitative()
