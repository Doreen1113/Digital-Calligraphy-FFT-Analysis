"""實驗四：跨資料集外部驗證。

用本資料集全部 7,449 張訓練 7 類 ResNet-18，
在 zhuojg/chinese-calligraphy-dataset（完全不同來源、不同掃描/裁切管線）
的楷書組 40,160 張上測試重疊的 6 位書法家。
預測時只在 6 個重疊類別的 logits 上取 argmax（歐陽詢不在外部集中）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ResNet18_Weights, resnet18

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize  # noqa: E402
from run_cnn import CalliDataset, DEV  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
EXT = Path("/home/intern_2603055/projects/tuijian/external_data/zhuojg_kai")

import cv2


class ExternalDataset(Dataset):
    def __init__(self, files: list[Path], y: np.ndarray):
        self.files, self.y = files, y
        self.tf = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
        ])

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        img = np.array(Image.open(self.files[i]).convert("L"))
        ink = binarize(img)
        ink = cv2.resize(ink, (224, 224), interpolation=cv2.INTER_AREA)
        rgb = np.stack([ink] * 3, axis=-1)
        return self.tf(rgb), int(self.y[i])


def main(seeds=2, epochs=15):
    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())          # 7 類（字母序）
    lab2i = {l: i for i, l in enumerate(labels)}
    y_all = manifest["label"].map(lab2i).values

    ext_labels = sorted(d.name for d in EXT.iterdir() if d.is_dir())   # 6 類
    keep_idx = [lab2i[l] for l in ext_labels]                          # 7→6 對映
    files, ys = [], []
    for l in ext_labels:
        fs = sorted((EXT / l).glob("*.gif"))
        files += fs
        ys += [ext_labels.index(l)] * len(fs)
    ys = np.array(ys)
    print(f"外部測試集: {len(files)} 張, 類別 {ext_labels}", flush=True)

    rows = []
    for seed in range(seeds):
        ds_tr = CalliDataset(manifest, y_all, train=True)
        dl_tr = DataLoader(ds_tr, batch_size=64, shuffle=True, num_workers=8, pin_memory=True)
        torch.manual_seed(seed)
        m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        m.fc = nn.Linear(m.fc.in_features, 7)
        m = m.to(DEV)
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
        lossf = nn.CrossEntropyLoss()
        for ep in range(epochs):
            m.train()
            for xb, yb in dl_tr:
                opt.zero_grad()
                lossf(m(xb.to(DEV)), yb.to(DEV)).backward()
                opt.step()

        m.eval()
        dl_te = DataLoader(ExternalDataset(files, ys), batch_size=128, num_workers=8)
        preds, gts = [], []
        with torch.no_grad():
            for xb, yb in dl_te:
                logits = m(xb.to(DEV))[:, keep_idx]      # 只看 6 個重疊類
                preds.append(logits.argmax(1).cpu().numpy())
                gts.append(yb.numpy())
        preds, gts = np.concatenate(preds), np.concatenate(gts)
        acc = accuracy_score(gts, preds)
        rows.append({"seed": seed, "acc": acc})
        print(f"seed{seed} 外部測試 acc={acc:.4f}（chance={1/len(ext_labels):.3f}）", flush=True)
        if seed == 0:
            cm = confusion_matrix(gts, preds)
            per_class = cm.diagonal() / cm.sum(1)
            for l, a in zip(ext_labels, per_class):
                print(f"   {l:15s} {a:.3f}", flush=True)
            np.savez(EXP / "cm_external.npz", labels=np.array(ext_labels), cm=cm)

    df = pd.DataFrame(rows)
    df.to_csv(EXP / "results_external.csv", index=False)
    print(df["acc"].agg(["mean", "std"]).round(4).to_string())


if __name__ == "__main__":
    main()
