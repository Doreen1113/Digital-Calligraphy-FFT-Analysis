"""實驗三：同字配對風格驗證（本資料集的獨門結構）。

任務：給兩張「同一個字」的圖，判斷是否出自同一位書法家。
把「字形內容」變因完全控制掉，只留「風格」訊號——公開資料集
（單張標籤）無法構成這種 text-dependent 設計。

做法：
1. 用訓練字（char-disjoint 的 train 部分）訓練 ResNet-18 分類器，
   取倒數第二層 512 維當風格 embedding。
2. 在測試字上蒐集所有「同字、不同來源」的圖片對：
   正例 = 同字同書法家（不同字帖/不同實例），負例 = 同字不同書法家。
3. 以 cosine 相似度計算 ROC-AUC；對照組用傳統 FD 特徵距離。
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader
from torchvision.models import ResNet18_Weights, resnet18

sys.path.insert(0, str(Path(__file__).parent))
from run_classical import char_disjoint_split, extract_features  # noqa: E402
from run_cnn import CalliDataset, DEV  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent


def train_embedder(manifest, y_all, tr, seed, epochs=12):
    ds_tr = CalliDataset(manifest[tr], y_all[tr], train=True)
    dl_tr = DataLoader(ds_tr, batch_size=64, shuffle=True, num_workers=8, pin_memory=True)
    torch.manual_seed(seed)
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.fc = nn.Linear(model.fc.in_features, 7)
    model = model.to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    lossf = nn.CrossEntropyLoss()
    for _ in range(epochs):
        model.train()
        for xb, yb in dl_tr:
            opt.zero_grad()
            lossf(model(xb.to(DEV)), yb.to(DEV)).backward()
            opt.step()
    model.fc = nn.Identity()
    model.eval()
    return model


def embed(model, manifest, y_all, mask):
    ds = CalliDataset(manifest[mask], y_all[mask], train=False)
    dl = DataLoader(ds, batch_size=128, num_workers=4)
    outs = []
    with torch.no_grad():
        for xb, _ in dl:
            outs.append(model(xb.to(DEV)).cpu().numpy())
    return np.concatenate(outs)


def build_pairs(df: pd.DataFrame, max_neg_per_char=60, rng=None):
    """回傳 (i, j, same) 的索引對；i, j 是 df 的列位置。"""
    pairs = []
    for _, grp in df.groupby("char"):
        idxs = grp.index.to_numpy()
        if len(idxs) < 2:
            continue
        cand = list(combinations(idxs, 2))
        pos = [(a, b) for a, b in cand if df.at[a, "label"] == df.at[b, "label"]]
        neg = [(a, b) for a, b in cand if df.at[a, "label"] != df.at[b, "label"]]
        if len(neg) > max_neg_per_char:
            sel = rng.choice(len(neg), max_neg_per_char, replace=False)
            neg = [neg[k] for k in sel]
        pairs += [(a, b, 1) for a, b in pos] + [(a, b, 0) for a, b in neg]
    return pairs


def cosine(a, b):
    return np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1) + 1e-12)


def main(seeds=3):
    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    y_all = manifest["label"].map({l: i for i, l in enumerate(labels)}).values
    feats = extract_features(manifest)          # 快取好的傳統特徵
    fd_all = np.nan_to_num(np.concatenate([feats[k] for k in feats], axis=1))

    rows = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        tr, te = char_disjoint_split(manifest, seed)
        te_df = manifest[te].copy()
        pairs = build_pairs(te_df, rng=rng)
        same = np.array([s for _, _, s in pairs])
        print(f"seed{seed}: 測試字配對 {len(pairs)} 組（正例 {same.sum()}，負例 {(1 - same).sum()}）", flush=True)

        # CNN embedding
        model = train_embedder(manifest, y_all, tr, seed)
        pos_in_te = {orig: k for k, orig in enumerate(te_df.index)}
        emb = embed(model, manifest, y_all, te)
        ea = emb[[pos_in_te[a] for a, _, _ in pairs]]
        eb = emb[[pos_in_te[b] for _, b, _ in pairs]]
        auc_cnn = roc_auc_score(same, cosine(ea, eb))

        # 傳統特徵（標準化後 cosine）
        mu, sd = fd_all[tr].mean(0), fd_all[tr].std(0) + 1e-9
        z = (fd_all - mu) / sd
        fa = z[[a for a, _, _ in pairs]]
        fb = z[[b for _, b, _ in pairs]]
        auc_fd = roc_auc_score(same, cosine(fa, fb))

        rows.append({"seed": seed, "auc_cnn": auc_cnn, "auc_classical": auc_fd})
        print(f"seed{seed} AUC: cnn={auc_cnn:.4f} classical={auc_fd:.4f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(EXP / "results_pairverify.csv", index=False)
    print(df[["auc_cnn", "auc_classical"]].agg(["mean", "std"]).round(4).to_string())


if __name__ == "__main__":
    main()
