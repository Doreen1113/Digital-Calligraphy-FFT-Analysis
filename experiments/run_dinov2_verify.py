"""現代方法對照：DINOv2 零訓練 embedding 的同字配對驗證。

不做任何訓練，直接用自監督基礎模型 DINOv2 (ViT-S/14) 抽特徵、
cosine 相似度做「這兩張同字是否同一書法家」。
對照組：我們訓練的 ResNet-18 embedding（AUC 0.998）與傳統特徵（0.635）。
回答：任務難度到底在哪——需要書法領域訓練，還是通用視覺特徵就夠？
"""
import sys
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from features import binarize
from run_classical import char_disjoint_split
from run_pairverify import build_pairs, cosine

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def main(seeds=3):
    model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14")
    model = model.to(DEV).eval()
    from torchvision import transforms
    tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    manifest = pd.read_csv(EXP / "manifest.csv")

    # 全部影像抽一次特徵（快取）
    cache = EXP / "cache" / "dinov2_feats.npy"
    if cache.exists():
        feats = np.load(cache)
    else:
        feats = []
        with torch.no_grad():
            batch = []
            for p in manifest["path"]:
                ink = binarize(cv2.imread(str(ROOT / p), cv2.IMREAD_GRAYSCALE))
                ink = cv2.resize(ink, (224, 224), interpolation=cv2.INTER_AREA)
                batch.append(tf(np.stack([ink] * 3, -1)))
                if len(batch) == 128:
                    feats.append(model(torch.stack(batch).to(DEV)).cpu().numpy())
                    batch = []
            if batch:
                feats.append(model(torch.stack(batch).to(DEV)).cpu().numpy())
        feats = np.concatenate(feats)
        np.save(cache, feats)

    rows = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        _, te = char_disjoint_split(manifest, seed)
        te_df = manifest[te].copy()
        pairs = build_pairs(te_df, rng=rng)
        same = np.array([s for _, _, s in pairs])
        pos_in_all = {orig: orig for orig in te_df.index}   # feats 以 manifest 全索引排列
        ea = feats[[a for a, _, _ in pairs]]
        eb = feats[[b for _, b, _ in pairs]]
        auc = roc_auc_score(same, cosine(ea, eb))
        rows.append({"seed": seed, "auc_dinov2": auc})
        print(f"seed{seed} DINOv2 zero-training AUC={auc:.4f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(EXP / "results_dinov2_verify.csv", index=False)
    print(df["auc_dinov2"].agg(["mean", "std"]).round(4).to_string())


if __name__ == "__main__":
    main()
