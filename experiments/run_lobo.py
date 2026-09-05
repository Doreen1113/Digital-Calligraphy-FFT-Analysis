"""留一字帖（leave-one-book-out）：7 類 CNN 訓練時排除沈尹默某本字帖，
測試該字帖是否仍被認出為沈尹默——風格跨字帖泛化的最直接證據。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score
from torch.utils.data import DataLoader
from torchvision.models import ResNet18_Weights, resnet18

sys.path.insert(0, str(Path(__file__).parent))
from run_cnn import CalliDataset, DEV  # noqa: E402

EXP = Path(__file__).parent
manifest = pd.read_csv(EXP / "manifest.csv")
labels = sorted(manifest["label"].unique())
y_all = manifest["label"].map({l: i for i, l in enumerate(labels)}).values

rows = []
for held in ["shen_yinmo_01", "shen_yinmo_08", "shen_yinmo_10"]:
    for seed in range(2):
        tr = (manifest["book"] != held).values
        te = ~tr
        ds_tr = CalliDataset(manifest[tr], y_all[tr], train=True)
        ds_te = CalliDataset(manifest[te], y_all[te], train=False)
        dl_tr = DataLoader(ds_tr, batch_size=64, shuffle=True, num_workers=8)
        dl_te = DataLoader(ds_te, batch_size=128, num_workers=4)
        torch.manual_seed(seed)
        m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        m.fc = nn.Linear(m.fc.in_features, 7)
        m = m.to(DEV)
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
        lossf = nn.CrossEntropyLoss()
        for _ in range(10):
            m.train()
            for xb, yb in dl_tr:
                opt.zero_grad()
                lossf(m(xb.to(DEV)), yb.to(DEV)).backward()
                opt.step()
        m.eval()
        preds, ys = [], []
        with torch.no_grad():
            for xb, yb in dl_te:
                preds.append(m(xb.to(DEV)).argmax(1).cpu().numpy())
                ys.append(yb.numpy())
        acc = accuracy_score(np.concatenate(ys), np.concatenate(preds))
        rows.append({"held_book": held, "seed": seed, "acc": acc})
        print(f"{held} seed{seed}: 認出為沈尹默的比例 = {acc:.4f}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(EXP / "results_lobo.csv", index=False)
print(df.groupby("held_book")["acc"].agg(["mean"]).round(4).to_string())
