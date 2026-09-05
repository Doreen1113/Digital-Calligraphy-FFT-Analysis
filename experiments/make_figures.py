"""把四個實驗的結果畫成報告用圖表（輸出到 experiments/figures/）。"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EXP = Path(__file__).parent
FIG = EXP / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 11, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False})
C = {"classical": "#4C72B0", "cnn": "#C44E52", "gray": "#888888"}

# ── 圖 1：分類準確率總覽 ─────────────────────────────────────────────────────
df = pd.read_csv(EXP / "results_classical.csv")
cnn = pd.read_csv(EXP / "results_cnn_pretrained.csv")
best = (df.groupby(["features", "clf"])["acc"].mean()
          .groupby("features").max())
order = ["spectral7", "hu", "fd", "all"]
names = ["Spectral-7\n(original)", "Hu moments", "Fourier desc.\n(ours)",
         "All handcrafted\n(SVM)"]
vals = [best[k] for k in order] + [cnn["acc"].mean()]
stds = [df[df.features == k].groupby("clf")["acc"].mean().max() * 0 +
        df[df.features == k].groupby("seed")["acc"].max().std() for k in order]
stds += [cnn["acc"].std()]
names += ["ResNet-18"]
colors = [C["classical"]] * 4 + [C["cnn"]]

fig, ax = plt.subplots(figsize=(7.2, 4.2))
x = np.arange(len(vals))
ax.bar(x, vals, yerr=stds, color=colors, width=0.62, capsize=4)
ax.axhline(0.2565, ls="--", c=C["gray"], lw=1)
ax.text(len(vals) - 0.4, 0.262, "majority class", c=C["gray"], fontsize=9)
ax.axhline(1 / 7, ls=":", c=C["gray"], lw=1)
ax.text(len(vals) - 0.4, 0.148, "chance", c=C["gray"], fontsize=9)
for xi, v in zip(x, vals):
    ax.text(xi, v + 0.025, f"{v:.1%}", ha="center", fontweight="bold", fontsize=10)
ax.set_xticks(x, names, fontsize=9)
ax.set_ylim(0, 1.09)
ax.set_ylabel("Test accuracy (character-disjoint)")
ax.set_title("7-way calligrapher classification, 7,449 samples, 5 seeds")
fig.tight_layout()
fig.savefig(FIG / "fig1_classification.png")

# ── 圖 2：FD 諧波數量掃描 ────────────────────────────────────────────────────
sw = pd.read_csv(EXP / "results_fd_sweep.csv").groupby("n_coeffs")["acc"].agg(["mean", "std"])
fig, ax = plt.subplots(figsize=(5.6, 4.0))
ax.errorbar(sw.index, sw["mean"], yerr=sw["std"], marker="o",
            color=C["classical"], capsize=3)
ax.set_xscale("log", base=2)
ax.set_xticks(sw.index, sw.index)
ax.axhline(0.2565, ls="--", c=C["gray"], lw=1)
ax.text(1, 0.262, "majority class", c=C["gray"], fontsize=9)
ax.set_xlabel("Number of contour Fourier harmonics (±n)")
ax.set_ylabel("SVM test accuracy")
ax.set_title("Style information vs. contour frequency content")
fig.tight_layout()
fig.savefig(FIG / "fig2_fd_sweep.png")

# ── 圖 3：2D 低通 × CNN ─────────────────────────────────────────────────────
lp = pd.read_csv(EXP / "results_lowpass_sweep.csv").groupby("cutoff")["acc"].agg(["mean", "std"])
fig, ax = plt.subplots(figsize=(5.6, 4.0))
ax.errorbar(lp.index, lp["mean"], yerr=lp["std"], marker="s",
            color=C["cnn"], capsize=3)
ax.set_xscale("log")
ax.set_xticks(lp.index, [f"{c:g}" for c in lp.index])
ax.set_xlabel("Radial low-pass cutoff (fraction of Nyquist)")
ax.set_ylabel("ResNet-18 test accuracy")
ax.set_title("How much spatial frequency does style need?")
ax.annotate("95% acc with only 10%\nof spatial frequencies",
            xy=(0.1, lp.loc[0.1, "mean"]), xytext=(0.03, 0.62),
            arrowprops=dict(arrowstyle="->", color="#333"), fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "fig3_lowpass.png")

# ── 圖 4：同字配對驗證 ───────────────────────────────────────────────────────
pv = pd.read_csv(EXP / "results_pairverify.csv")
fig, ax = plt.subplots(figsize=(4.6, 4.0))
means = [pv["auc_classical"].mean(), pv["auc_cnn"].mean()]
errs = [pv["auc_classical"].std(), pv["auc_cnn"].std()]
ax.bar([0, 1], means, yerr=errs, width=0.5,
       color=[C["classical"], C["cnn"]], capsize=5)
ax.axhline(0.5, ls="--", c=C["gray"], lw=1)
ax.text(1.15, 0.505, "chance", c=C["gray"], fontsize=9)
for xi, v in zip([0, 1], means):
    ax.text(xi, v + 0.02, f"{v:.3f}", ha="center", fontweight="bold")
ax.set_xticks([0, 1], ["Handcrafted\nfeatures", "CNN style\nembedding"])
ax.set_ylim(0.4, 1.06)
ax.set_ylabel("ROC-AUC")
ax.set_title("Same-character pair verification\n(unseen characters)")
fig.tight_layout()
fig.savefig(FIG / "fig4_pairverify.png")

print("figures saved:", sorted(p.name for p in FIG.glob("*.png")))
