"""圖 0：傅立葉漸進重建圖——《筆頻》的研究化版本。

取資料集中一個真實書法字，對其輪廓做傅立葉分解，
以 n = 1, 2, 4, 8, 16, 64 個諧波重建，排成一列：
「字的身份住在前幾個頻率裡」的視覺證明，對應低通消融實驗的量化曲線。
同時輸出逐格 GIF（供網頁當動畫用）。
"""
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent))
from features import binarize, contours_of

ROOT = Path(__file__).parent.parent
FIG = Path(__file__).parent / "figures"

# 顏真卿的「敬」（char_0041 是多寶塔碑裡結構漂亮的字）
SRC = ROOT / "Fonts" / "my_fonts" / "02" / "char_0041.png"
NS = [1, 2, 4, 8, 16, 64]


def reconstruct(cnt: np.ndarray, n: int, n_resample: int = 512) -> np.ndarray:
    d = np.diff(cnt, axis=0, append=cnt[:1])
    seglen = np.hypot(d[:, 0], d[:, 1])
    arc = np.concatenate([[0], np.cumsum(seglen)])[:-1]
    total = arc[-1] + seglen[-1]
    t = np.linspace(0, total, n_resample, endpoint=False)
    x = np.interp(t, arc, cnt[:, 0], period=total)
    y = np.interp(t, arc, cnt[:, 1], period=total)
    Z = np.fft.fft(x + 1j * y)
    keep = np.zeros_like(Z)
    keep[0] = Z[0]
    keep[1:n + 1] = Z[1:n + 1]
    keep[-n:] = Z[-n:]
    rec = np.fft.ifft(keep)
    return np.stack([rec.real, rec.imag], axis=1)


def main():
    img = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE)
    ink = binarize(img)
    cnts = contours_of(ink, min_len=24, max_contours=24)

    fig, axes = plt.subplots(1, len(NS) + 1, figsize=(2.1 * (len(NS) + 1), 2.4))
    for ax in axes:
        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.axis("off")

    from matplotlib.font_manager import FontProperties
    cjk = FontProperties(fname="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf")

    for j, n in enumerate(NS):
        for cnt in cnts:
            rec = reconstruct(cnt, n)
            axes[j].fill(rec[:, 0], rec[:, 1], color="#1a1a1a", alpha=0.92, lw=0)
        axes[j].set_title(f"n = {n}", fontsize=11)

    axes[-1].imshow(ink, cmap="gray_r")
    axes[-1].set_title("原字・顏真卿", fontsize=11, fontproperties=cjk)
    fig.tight_layout()
    fig.savefig(FIG / "fig0_reconstruction.png", dpi=170, bbox_inches="tight", facecolor="white")
    print("saved", FIG / "fig0_reconstruction.png")

    # ── GIF：諧波數從 1 掃到 64 ──
    import matplotlib.animation as anim
    ns_anim = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64]
    figa, axa = plt.subplots(figsize=(3.2, 3.2))
    axa.set_aspect("equal")
    axa.axis("off")

    xs = np.concatenate([c[:, 0] for c in cnts])
    ys = np.concatenate([c[:, 1] for c in cnts])
    pad = 12

    def draw(i):
        axa.clear()
        axa.set_aspect("equal")
        axa.axis("off")
        axa.set_xlim(xs.min() - pad, xs.max() + pad)
        axa.set_ylim(ys.max() + pad, ys.min() - pad)
        n = ns_anim[i % len(ns_anim)]
        for cnt in cnts:
            rec = reconstruct(cnt, n)
            axa.fill(rec[:, 0], rec[:, 1], color="#1a1a1a", alpha=0.92, lw=0)
        axa.text(0.02, 0.02, f"n = {n}", transform=axa.transAxes, fontsize=13)

    a = anim.FuncAnimation(figa, draw, frames=len(ns_anim), interval=280)
    a.save(FIG / "fig0_reconstruction.gif", writer="pillow", dpi=100)
    print("saved", FIG / "fig0_reconstruction.gif")


if __name__ == "__main__":
    main()
