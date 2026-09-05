"""驗證導引重排（verification-guided reranking）評估。

對多候選生成結果（run_generation --n_candidates K）：
1. 用「選擇器」（獨立訓練，seed=1，與凍結評估器不同權重）
   為每個 (書法家, 字) 的 K 個候選打分，選目標書法家機率最高者。
2. 被選中的集合再用「凍結評估器」（seed=0，eval_classifier.pth）算 style match，
   與 SSIM。選擇器 ≠ 評估器，避免循環自證。
"""
from __future__ import annotations

import argparse
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
from features import binarize  # noqa: E402
from run_cnn import CalliDataset, DEV  # noqa: E402
from run_gen_eval import BOOK2LABEL, load_ink  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
TF = transforms.Compose([transforms.ToTensor(), transforms.Normalize([0.5] * 3, [0.5] * 3)])


def get_model(ckpt: Path, seed: int, manifest, y_all):
    m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    m.fc = nn.Linear(m.fc.in_features, 7)
    m = m.to(DEV)
    if ckpt.exists():
        m.load_state_dict(torch.load(ckpt, map_location=DEV))
    else:
        torch.manual_seed(seed)
        dl = DataLoader(CalliDataset(manifest, y_all, train=True), batch_size=64,
                        shuffle=True, num_workers=8, pin_memory=True)
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
        lossf = nn.CrossEntropyLoss()
        for _ in range(10):
            m.train()
            for xb, yb in dl:
                opt.zero_grad()
                lossf(m(xb.to(DEV)), yb.to(DEV)).backward()
                opt.step()
        torch.save(m.state_dict(), ckpt)
    m.eval()
    return m


def probs(model, path):
    ink = load_ink(path)
    x = TF(np.stack([ink] * 3, -1)).unsqueeze(0).to(DEV)
    with torch.no_grad():
        return torch.softmax(model(x), dim=1)[0].cpu().numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen_dir", required=True)
    ap.add_argument("--tag", default="rerank")
    args = ap.parse_args()

    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    lab2i = {l: i for i, l in enumerate(labels)}
    y_all = manifest["label"].map(lab2i).values

    evaluator = get_model(EXP / "cache" / "eval_classifier.pth", 0, manifest, y_all)
    selector = get_model(EXP / "cache" / "selector_classifier.pth", 1, manifest, y_all)

    gm = pd.read_csv(Path(args.gen_dir) / "generation_manifest.csv")
    gm["target_i"] = gm["cal"].map(BOOK2LABEL).map(lab2i)

    picked, hits, ssims, oracle_hits = [], [], [], []
    for (cal, h), grp in gm.groupby(["cal", "hex"]):
        ti = int(grp["target_i"].iloc[0])
        sel_scores = [probs(selector, r["gen"])[ti] for _, r in grp.iterrows()]
        best = grp.iloc[int(np.argmax(sel_scores))]
        picked.append(best["gen"])
        ev = [int(np.argmax(probs(evaluator, r["gen"])) == ti) for _, r in grp.iterrows()]
        hits.append(int(np.argmax(probs(evaluator, best["gen"])) == ti))
        oracle_hits.append(max(ev))          # 理論上限：若選擇器完美
        a = load_ink(best["gen"], 256)
        b = load_ink(best["gt"], 256)
        ssims.append(ssim(a, b))

    n = len(hits)
    out = pd.DataFrame({
        "metric": ["style_match_reranked", "style_match_oracle_upper",
                   "ssim_reranked", "n_items", "k_candidates"],
        "value": [np.mean(hits), np.mean(oracle_hits), np.mean(ssims),
                  n, len(gm) / n],
    })
    out.to_csv(EXP / f"results_{args.tag}.csv", index=False)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
