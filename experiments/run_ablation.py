"""實驗二：頻域消融——「書法風格訊號住在哪個頻段？」

A 部分（輪廓 FD 係數數量掃描）：
  FD 只取前 n 個諧波（n = 1..64），SVM 分類準確率曲線。
  回答：輪廓的前幾個低頻諧波就承載多少風格資訊。

B 部分（2D 影像radial低通掃描 × CNN）：
  對整張二值字圖做 2D FFT radial 低通（保留半徑 r 內的頻率），
  訓練與測試都用同一 cutoff 的影像重新訓練 ResNet-18。
  回答：CNN 需要多高的空間頻率才能辨識風格——
  若低頻(整體結構)就夠，曲線很早飽和；若靠高頻(筆鋒細節)，曲線爬得慢。
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize, contours_of, fourier_descriptor  # noqa: E402
from run_classical import char_disjoint_split  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent


# ── A: FD 係數掃描 ───────────────────────────────────────────────────────────

def part_a(manifest, y_all, ns=(1, 2, 4, 8, 16, 32, 64), seeds=5):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    from sklearn.metrics import accuracy_score
    from tqdm import tqdm

    n_max = max(ns)
    cache = EXP / "cache" / f"fd_full_{n_max}.npz"
    if cache.exists():
        descs = np.load(cache)["descs"]
    else:
        descs = []
        for p in tqdm(manifest["path"], desc="FD full"):
            ink = binarize(cv2.imread(str(ROOT / p), cv2.IMREAD_GRAYSCALE))
            cnts = contours_of(ink)
            if not cnts:
                descs.append(np.zeros(4 * n_max))
                continue
            ds = np.array([fourier_descriptor(c, n_max) for c in cnts])
            w = np.array([len(c) for c in cnts], float)
            w /= w.sum()
            mean = (ds * w[:, None]).sum(axis=0)
            std = ds.std(axis=0) if len(ds) > 1 else np.zeros_like(mean)
            descs.append(np.concatenate([mean, std]))
        descs = np.array(descs)
        np.savez_compressed(cache, descs=descs)

    rows = []
    for n in ns:
        # 取 mean/std 各自的 ±1..±n 諧波欄位
        idx = np.r_[0:n, n_max:n_max + n,
                    2 * n_max:2 * n_max + n, 3 * n_max:3 * n_max + n]
        X = np.nan_to_num(descs[:, idx])
        for seed in range(seeds):
            tr, te = char_disjoint_split(manifest, seed)
            clf = make_pipeline(StandardScaler(), SVC(C=10, gamma="scale"))
            clf.fit(X[tr], y_all[tr])
            acc = accuracy_score(y_all[te], clf.predict(X[te]))
            rows.append({"n_coeffs": n, "seed": seed, "acc": acc})
            print(f"A: n={n:3d} seed{seed} acc={acc:.4f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(EXP / "results_fd_sweep.csv", index=False)
    print(df.groupby("n_coeffs")["acc"].agg(["mean", "std"]).round(4).to_string())


# ── B: 2D radial 低通 × CNN ──────────────────────────────────────────────────

def radial_lowpass(ink: np.ndarray, cutoff: float) -> np.ndarray:
    """保留半徑 cutoff（以 Nyquist 比例 0-1 表示）內的 2D 頻率成分。"""
    h, w = ink.shape
    F = np.fft.fftshift(np.fft.fft2(ink.astype(np.float32)))
    yy, xx = np.mgrid[-h // 2:h - h // 2, -w // 2:w - w // 2]
    r = np.sqrt((yy / (h / 2)) ** 2 + (xx / (w / 2)) ** 2)
    F[r > cutoff] = 0
    out = np.real(np.fft.ifft2(np.fft.ifftshift(F)))
    return np.clip(out, 0, 255).astype(np.uint8)


def part_b(manifest, y_all, cutoffs=(0.02, 0.05, 0.1, 0.2, 0.4, 1.0), seeds=2, epochs=10):
    import torch
    from run_cnn import CalliDataset, DEV
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision.models import ResNet18_Weights, resnet18
    from sklearn.metrics import accuracy_score

    class FilteredDS(CalliDataset):
        def __init__(self, df, y, train, cutoff):
            super().__init__(df, y, train)
            self.cutoff = cutoff

        def __getitem__(self, i):
            img = cv2.imread(str(ROOT / self.paths[i]), cv2.IMREAD_GRAYSCALE)
            ink = binarize(img)
            if self.cutoff < 1.0:
                ink = radial_lowpass(ink, self.cutoff)
            ink = cv2.resize(ink, (224, 224), interpolation=cv2.INTER_AREA)
            rgb = np.stack([ink] * 3, axis=-1)
            return self.tf(rgb), int(self.y[i])

    rows = []
    for cutoff in cutoffs:
        for seed in range(seeds):
            tr, te = char_disjoint_split(manifest, seed)
            ds_tr = FilteredDS(manifest[tr], y_all[tr], True, cutoff)
            ds_te = FilteredDS(manifest[te], y_all[te], False, cutoff)
            dl_tr = DataLoader(ds_tr, batch_size=64, shuffle=True, num_workers=8, pin_memory=True)
            dl_te = DataLoader(ds_te, batch_size=128, num_workers=4)

            torch.manual_seed(seed)
            model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
            model.fc = nn.Linear(model.fc.in_features, 7)
            model = model.to(DEV)
            opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
            lossf = nn.CrossEntropyLoss()
            for ep in range(epochs):
                model.train()
                for xb, yb in dl_tr:
                    opt.zero_grad()
                    lossf(model(xb.to(DEV)), yb.to(DEV)).backward()
                    opt.step()
            model.eval()
            preds, ys = [], []
            with torch.no_grad():
                for xb, yb in dl_te:
                    preds.append(model(xb.to(DEV)).argmax(1).cpu().numpy())
                    ys.append(yb.numpy())
            acc = accuracy_score(np.concatenate(ys), np.concatenate(preds))
            rows.append({"cutoff": cutoff, "seed": seed, "acc": acc})
            print(f"B: cutoff={cutoff} seed{seed} acc={acc:.4f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(EXP / "results_lowpass_sweep.csv", index=False)
    print(df.groupby("cutoff")["acc"].agg(["mean", "std"]).round(4).to_string())


if __name__ == "__main__":
    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    y_all = manifest["label"].map({l: i for i, l in enumerate(labels)}).values
    part_a(manifest, y_all)
    part_b(manifest, y_all)
