"""混淆檢查：模型學的是「書法家風格」還是「字帖來源」？

R1 各字帖低階統計特徵（筆畫平均寬度、墨跡比例）——字帖之間若差很大，
   就存在可被模型利用的來源訊號。
R2 字帖分類（沈尹默 4 本，同一人）：char-disjoint 下若能輕鬆分辨
   同一人的不同字帖，代表「字帖簽名」很強，7 類結果被灌水。
R3 驗證 AUC 拆解：同字配對的正例分成「同字帖」與「跨字帖」（沈尹默限定），
   若跨字帖 AUC 明顯低於同字帖，配對驗證的 0.998 有一部分是認字帖。
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize  # noqa: E402
from run_classical import char_disjoint_split  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent


# ── R1: 每本字帖的低階統計 ───────────────────────────────────────────────────

def stroke_width_stats(ink: np.ndarray) -> tuple[float, float]:
    """平均筆畫寬度（distance transform 峰值×2）與墨跡比例。"""
    dist = cv2.distanceTransform((ink > 0).astype(np.uint8), cv2.DIST_L2, 5)
    widths = dist[dist > 0]
    mean_w = 2 * float(widths.mean()) if len(widths) else 0.0
    return mean_w, float((ink > 0).mean())


def r1(manifest):
    rng = np.random.default_rng(0)
    rows = []
    for book, grp in manifest.groupby("book"):
        take = grp.sample(min(120, len(grp)), random_state=0)
        ws, inks, sizes = [], [], []
        for p in take["path"]:
            raw = cv2.imread(str(ROOT / p), cv2.IMREAD_GRAYSCALE)
            sizes.append(raw.shape[0] * raw.shape[1])
            ink = binarize(raw)
            w, ir = stroke_width_stats(ink)
            ws.append(w)
            inks.append(ir)
        rows.append({"book": book, "n": len(grp),
                     "stroke_w_mean": np.mean(ws), "stroke_w_std": np.std(ws),
                     "ink_ratio": np.mean(inks),
                     "img_px_median": int(np.median(sizes))})
    df = pd.DataFrame(rows)
    df.to_csv(EXP / "confound_book_stats.csv", index=False)
    print("== R1 各字帖統計（256×256 正規化後）==")
    print(df.round(3).to_string(index=False))


# ── R2: 沈尹默 4 本字帖互分 ──────────────────────────────────────────────────

def r2(manifest, seeds=3, epochs=10):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision.models import ResNet18_Weights, resnet18
    from sklearn.metrics import accuracy_score
    from run_cnn import CalliDataset, DEV

    sub = manifest[manifest["label"] == "shen_yinmo"].reset_index(drop=True)
    books = sorted(sub["book"].unique())
    y = sub["book"].map({b: i for i, b in enumerate(books)}).values
    print(f"\n== R2 沈尹默字帖分類（{len(sub)} 張，{len(books)} 本）==")
    maj = pd.Series(y).value_counts(normalize=True).iloc[0]
    accs = []
    for seed in range(seeds):
        tr, te = char_disjoint_split(sub, seed)
        ds_tr = CalliDataset(sub[tr], y[tr], train=True)
        ds_te = CalliDataset(sub[te], y[te], train=False)
        dl_tr = DataLoader(ds_tr, batch_size=64, shuffle=True, num_workers=8)
        dl_te = DataLoader(ds_te, batch_size=128, num_workers=4)
        torch.manual_seed(seed)
        model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        model.fc = nn.Linear(model.fc.in_features, len(books))
        model = model.to(DEV)
        opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
        lossf = nn.CrossEntropyLoss()
        for _ in range(epochs):
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
        accs.append(acc)
        print(f"  seed{seed} acc={acc:.4f}", flush=True)
    print(f"  mean={np.mean(accs):.4f}  多數類 baseline={maj:.4f}")
    pd.DataFrame({"seed": range(seeds), "acc": accs}).to_csv(
        EXP / "confound_book_clf.csv", index=False)


# ── R3: 驗證 AUC 拆解（同字帖 vs 跨字帖正例）────────────────────────────────

def r3(manifest, seeds=3):
    from sklearn.metrics import roc_auc_score
    from run_pairverify import train_embedder, embed, cosine

    labels = sorted(manifest["label"].unique())
    y_all = manifest["label"].map({l: i for i, l in enumerate(labels)}).values
    print("\n== R3 驗證 AUC 拆解 ==")
    rows = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        tr, te = char_disjoint_split(manifest, seed)
        te_df = manifest[te].copy()
        model = train_embedder(manifest, y_all, tr, seed)
        emb = embed(model, manifest, y_all, te)
        pos_in_te = {orig: k for k, orig in enumerate(te_df.index)}

        same_book_pairs, cross_book_pairs, neg_pairs = [], [], []
        for _, grp in te_df.groupby("char"):
            for a, b in combinations(grp.index, 2):
                la, lb = te_df.at[a, "label"], te_df.at[b, "label"]
                ba, bb = te_df.at[a, "book"], te_df.at[b, "book"]
                if la == lb:
                    (same_book_pairs if ba == bb else cross_book_pairs).append((a, b))
                else:
                    neg_pairs.append((a, b))
        if len(neg_pairs) > 4000:
            sel = rng.choice(len(neg_pairs), 4000, replace=False)
            neg_pairs = [neg_pairs[k] for k in sel]

        def auc_for(pos):
            pairs = pos + neg_pairs
            same = np.array([1] * len(pos) + [0] * len(neg_pairs))
            ea = emb[[pos_in_te[a] for a, _ in pairs]]
            eb = emb[[pos_in_te[b] for _, b in pairs]]
            return roc_auc_score(same, cosine(ea, eb))

        auc_same = auc_for(same_book_pairs) if same_book_pairs else float("nan")
        auc_cross = auc_for(cross_book_pairs) if cross_book_pairs else float("nan")
        rows.append({"seed": seed, "n_same_book_pos": len(same_book_pairs),
                     "n_cross_book_pos": len(cross_book_pairs),
                     "auc_same_book": auc_same, "auc_cross_book": auc_cross})
        print(f"  seed{seed} 同字帖正例 {len(same_book_pairs)} AUC={auc_same:.4f} | "
              f"跨字帖正例 {len(cross_book_pairs)} AUC={auc_cross:.4f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(EXP / "confound_auc_split.csv", index=False)
    print(df[["auc_same_book", "auc_cross_book"]].agg(["mean", "std"]).round(4).to_string())


if __name__ == "__main__":
    manifest = pd.read_csv(EXP / "manifest.csv")
    r1(manifest)
    r2(manifest)
    r3(manifest)
