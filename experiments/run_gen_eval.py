"""實驗五b：生成結果量化評估。

指標：
1. Style match rate — 用在全部真實資料上訓練的 7 類 ResNet-18 去分類生成字，
   看被判為目標書法家的比例。對照組：
   - 真跡 GT 本身（上限）
   - 標楷體 content 圖（sanity：不該像任何書法家）
2. SSIM — 生成 vs 同字真跡（二值化置中後）。
3. FD 特徵 cosine — 生成 vs 同字真跡 / vs 隨機他人同字真跡（風格是否更靠近目標）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from skimage.metrics import structural_similarity as ssim
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.models import ResNet18_Weights, resnet18

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize, fd_features  # noqa: E402
from run_cnn import CalliDataset, DEV  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
GEN = EXP / "generated"

BOOK2LABEL = {"zhiyong_00": "zhiyong", "ouyang_xun_03": "ouyang_xun",
              "yu_shinan_06": "yu_shinan", "yan_zhenqing_07": "yan_zhenqing",
              "liu_gongquan_02": "liu_gongquan", "zhao_mengfu_04": "zhao_mengfu",
              "shen_yinmo_01": "shen_yinmo"}


def load_ink(path, size=224):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    ink = binarize(img)
    return cv2.resize(ink, (size, size), interpolation=cv2.INTER_AREA)


def classify(model, tf, paths):
    preds = []
    with torch.no_grad():
        for p in paths:
            ink = load_ink(p)
            x = tf(np.stack([ink] * 3, -1)).unsqueeze(0).to(DEV)
            preds.append(model(x).argmax(1).item())
    return np.array(preds)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen_dir", default=str(GEN), help="生成結果目錄（含 generation_manifest.csv）")
    ap.add_argument("--tag", default="", help="結果檔名後綴，如 ft5000")
    args = ap.parse_args()
    gen_dir = Path(args.gen_dir)
    gm = pd.read_csv(gen_dir / "generation_manifest.csv")
    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    lab2i = {l: i for i, l in enumerate(labels)}
    y_all = manifest["label"].map(lab2i).values

    # ── 訓練 style 分類器（全部真實資料）──
    torch.manual_seed(0)
    dl = DataLoader(CalliDataset(manifest, y_all, train=True), batch_size=64,
                    shuffle=True, num_workers=8, pin_memory=True)
    m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    m.fc = nn.Linear(m.fc.in_features, 7)
    m = m.to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
    lossf = nn.CrossEntropyLoss()
    for ep in range(10):
        m.train()
        for xb, yb in dl:
            opt.zero_grad()
            lossf(m(xb.to(DEV)), yb.to(DEV)).backward()
            opt.step()
    m.eval()
    tf = transforms.Compose([transforms.ToTensor(),
                             transforms.Normalize([0.5] * 3, [0.5] * 3)])

    target = gm["cal"].map(BOOK2LABEL).map(lab2i).values
    match_gen = (classify(m, tf, gm["gen"]) == target).mean()
    match_gt = (classify(m, tf, gm["gt"]) == target).mean()
    match_content = (classify(m, tf, gm["content"]) == target).mean()

    # ── SSIM 與 FD cosine ──
    rng = np.random.default_rng(0)
    ssims, fd_gt, fd_other = [], [], []
    gt_by_cal = {c: g["gt"].tolist() for c, g in gm.groupby("cal")}
    for _, r in gm.iterrows():
        a, b = load_ink(r["gen"], 256), load_ink(r["gt"], 256)
        ssims.append(ssim(a, b))
        fa = fd_features(a)
        fb = fd_features(b)
        cos = lambda u, v: float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
        fd_gt.append(cos(fa, fb))
        other_cal = rng.choice([c for c in gt_by_cal if c != r["cal"]])
        fo = fd_features(load_ink(rng.choice(gt_by_cal[other_cal]), 256))
        fd_other.append(cos(fa, fo))

    out = pd.DataFrame({
        "metric": ["style_match_generated", "style_match_ground_truth",
                   "style_match_content(下限)", "ssim_gen_vs_gt",
                   "fd_cosine_gen_vs_gt", "fd_cosine_gen_vs_other"],
        "value": [match_gen, match_gt, match_content,
                  float(np.mean(ssims)), float(np.mean(fd_gt)), float(np.mean(fd_other))],
    })
    suffix = f"_{args.tag}" if args.tag else ""
    out.to_csv(EXP / f"results_generation{suffix}.csv", index=False)
    print(out.round(4).to_string(index=False))

    per_cal = gm.assign(hit=(classify(m, tf, gm["gen"]) == target)).groupby("cal")["hit"].mean()
    print("\n各書法家 style match rate:")
    print(per_cal.round(3).to_string())


if __name__ == "__main__":
    main()
