"""實驗一（深度學習組）：ResNet-18 書法家分類 baseline。

與 run_classical.py 使用完全相同的 character-disjoint split（同 seed 同切分），
確保傳統特徵與 CNN 的數字可直接比較。
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
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ResNet18_Weights, resnet18

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize  # noqa: E402
from run_classical import char_disjoint_split  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
DEV = "cuda" if torch.cuda.is_available() else "cpu"


class CalliDataset(Dataset):
    def __init__(self, df: pd.DataFrame, y: np.ndarray, train: bool):
        self.paths = df["path"].tolist()
        self.y = y
        aug = [transforms.RandomAffine(degrees=5, translate=(0.05, 0.05),
                                       scale=(0.9, 1.1), fill=0)] if train else []
        self.tf = transforms.Compose([
            transforms.ToTensor(),
            *aug,
            transforms.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
        ])

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        img = cv2.imread(str(ROOT / self.paths[i]), cv2.IMREAD_GRAYSCALE)
        ink = binarize(img)                      # 與傳統特徵完全相同的前處理
        ink = cv2.resize(ink, (224, 224), interpolation=cv2.INTER_AREA)
        rgb = np.stack([ink] * 3, axis=-1)
        return self.tf(rgb), int(self.y[i])


def run_seed(manifest, y_all, seed, epochs, scratch=False):
    tr, te = char_disjoint_split(manifest, seed)
    # 從 train 再切一小塊字當 val（early model selection 用 test 會作弊）
    tr_df = manifest[tr].reset_index(drop=True)
    tr_in, va_in = char_disjoint_split(tr_df, seed + 1000, test_ratio=0.12)

    ds_tr = CalliDataset(tr_df[tr_in], y_all[tr][tr_in], train=True)
    ds_va = CalliDataset(tr_df[va_in], y_all[tr][va_in], train=False)
    ds_te = CalliDataset(manifest[te], y_all[te], train=False)
    dl_tr = DataLoader(ds_tr, batch_size=64, shuffle=True, num_workers=8, pin_memory=True)
    dl_va = DataLoader(ds_va, batch_size=128, num_workers=4)
    dl_te = DataLoader(ds_te, batch_size=128, num_workers=4)

    torch.manual_seed(seed)
    weights = None if scratch else ResNet18_Weights.IMAGENET1K_V1
    model = resnet18(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, 7)
    model = model.to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    lossf = nn.CrossEntropyLoss()

    best_va, best_state = 0.0, None
    for ep in range(epochs):
        model.train()
        for xb, yb in dl_tr:
            xb, yb = xb.to(DEV, non_blocking=True), yb.to(DEV)
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
        sched.step()
        model.eval()
        correct = n = 0
        with torch.no_grad():
            for xb, yb in dl_va:
                pred = model(xb.to(DEV)).argmax(1).cpu()
                correct += (pred == yb).sum().item()
                n += len(yb)
        va = correct / n
        if va > best_va:
            best_va, best_state = va, {k: v.clone() for k, v in model.state_dict().items()}
        print(f"  seed{seed} ep{ep + 1}/{epochs} val_acc={va:.4f}", flush=True)

    model.load_state_dict(best_state)
    model.eval()
    preds, ys = [], []
    with torch.no_grad():
        for xb, yb in dl_te:
            preds.append(model(xb.to(DEV)).argmax(1).cpu().numpy())
            ys.append(yb.numpy())
    preds, ys = np.concatenate(preds), np.concatenate(ys)
    return (accuracy_score(ys, preds), f1_score(ys, preds, average="macro"),
            confusion_matrix(ys, preds))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--scratch", action="store_true", help="不用 ImageNet 預訓練")
    args = ap.parse_args()

    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    y_all = manifest["label"].map({l: i for i, l in enumerate(labels)}).values

    tag = "scratch" if args.scratch else "pretrained"
    rows = []
    for seed in range(args.seeds):
        acc, f1, cm = run_seed(manifest, y_all, seed, args.epochs, args.scratch)
        rows.append({"seed": seed, "features": f"resnet18_{tag}", "clf": "cnn",
                     "acc": acc, "macro_f1": f1})
        print(f"seed{seed} TEST acc={acc:.4f} f1={f1:.4f}", flush=True)
        if seed == 0:
            np.savez(EXP / f"cm_cnn_{tag}.npz", labels=np.array(labels), cm=cm)

    df = pd.DataFrame(rows)
    df.to_csv(EXP / f"results_cnn_{tag}.csv", index=False)
    print(df[["acc", "macro_f1"]].agg(["mean", "std"]).round(4).to_string())


if __name__ == "__main__":
    main()
