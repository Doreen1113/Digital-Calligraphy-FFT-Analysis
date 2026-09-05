"""實驗四b：筆畫寬度正規化後的跨資料集驗證。

假設：跨資料集失敗主因是筆畫粗細/翻攝質感等來源訊號。
做法：訓練與測試影像都先骨架化（skeletonize）再以固定寬度膨脹重繪，
只保留純幾何結構。若準確率顯著回升，證明幾何結構本身可跨來源泛化，
且原始 in-dataset 高分中有一部分來自來源訊號——閉合整個研究故事。
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from skimage.morphology import skeletonize
from sklearn.metrics import accuracy_score, confusion_matrix
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ResNet18_Weights, resnet18

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize  # noqa: E402
from run_cnn import DEV  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
EXT = Path("/home/intern_2603055/projects/tuijian/external_data/zhuojg_kai")

STROKE_W = 5   # 重繪筆畫寬度（256px 座標系）


def normalize_stroke(ink: np.ndarray) -> np.ndarray:
    """骨架化 + 固定寬度重繪：消除筆畫粗細與邊緣質感差異。"""
    skel = skeletonize(ink > 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (STROKE_W, STROKE_W))
    return cv2.dilate(skel.astype(np.uint8) * 255, kernel)


class NormDataset(Dataset):
    def __init__(self, items, train: bool):
        """items: [(loader_fn, label), ...]"""
        self.items = items
        aug = [transforms.RandomAffine(degrees=5, translate=(0.05, 0.05),
                                       scale=(0.9, 1.1), fill=0)] if train else []
        self.tf = transforms.Compose([
            transforms.ToTensor(), *aug,
            transforms.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
        ])

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, y = self.items[i]
        arr = np.array(Image.open(path).convert("L"))
        ink = normalize_stroke(binarize(arr))
        ink = cv2.resize(ink, (224, 224), interpolation=cv2.INTER_AREA)
        return self.tf(np.stack([ink] * 3, axis=-1)), int(y)


def main(seeds=2, epochs=15):
    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    lab2i = {l: i for i, l in enumerate(labels)}
    train_items = [(str(ROOT / p), lab2i[l])
                   for p, l in zip(manifest["path"], manifest["label"])]

    ext_labels = sorted(d.name for d in EXT.iterdir() if d.is_dir())
    keep_idx = [lab2i[l] for l in ext_labels]
    test_items = []
    for j, l in enumerate(ext_labels):
        test_items += [(str(p), j) for p in sorted((EXT / l).glob("*.gif"))]
    print(f"train {len(train_items)} / external test {len(test_items)}", flush=True)

    rows = []
    for seed in range(seeds):
        dl_tr = DataLoader(NormDataset(train_items, True), batch_size=64,
                           shuffle=True, num_workers=12, pin_memory=True)
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
        dl_te = DataLoader(NormDataset(test_items, False), batch_size=128, num_workers=12)
        preds, gts = [], []
        with torch.no_grad():
            for xb, yb in dl_te:
                preds.append(m(xb.to(DEV))[:, keep_idx].argmax(1).cpu().numpy())
                gts.append(yb.numpy())
        preds, gts = np.concatenate(preds), np.concatenate(gts)
        acc = accuracy_score(gts, preds)
        rows.append({"seed": seed, "acc": acc})
        print(f"seed{seed} 正規化外部測試 acc={acc:.4f}", flush=True)
        if seed == 0:
            cm = confusion_matrix(gts, preds)
            for l, a in zip(ext_labels, cm.diagonal() / cm.sum(1)):
                print(f"   {l:15s} {a:.3f}", flush=True)
            np.savez(EXP / "cm_external_norm.npz", labels=np.array(ext_labels), cm=cm)

    pd.DataFrame(rows).to_csv(EXP / "results_external_norm.csv", index=False)


if __name__ == "__main__":
    main()
