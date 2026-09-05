"""實驗一：傳統特徵的書法家分類（7 類）。

設計重點：
- character-disjoint split：訓練/測試使用完全不重疊的「字」，
  模型只能靠風格泛化，不能靠記住某個字的長相。
- 每組特徵（fd / spectral7 / hu / 全部串接）× 每個分類器，重複 5 個 seed
  （每個 seed 重抽一次字的切分），報告 mean ± std。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from features import FEATURE_SETS, binarize  # noqa: E402

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent
CACHE = EXP / "cache"
CACHE.mkdir(exist_ok=True)


def extract_features(manifest: pd.DataFrame) -> dict[str, np.ndarray]:
    """逐張抽特徵（含快取）。回傳 {feature_set: (N, D)}。"""
    cache_file = CACHE / "classical_features.npz"
    if cache_file.exists():
        data = np.load(cache_file, allow_pickle=True)
        if len(data["fd"]) == len(manifest):
            return {k: data[k] for k in FEATURE_SETS}
    out = defaultdict(list)
    for p in tqdm(manifest["path"], desc="extract"):
        img = cv2.imread(str(ROOT / p), cv2.IMREAD_GRAYSCALE)
        ink = binarize(img)
        for name, fn in FEATURE_SETS.items():
            out[name].append(fn(ink))
    arrays = {k: np.array(v) for k, v in out.items()}
    np.savez_compressed(cache_file, **arrays)
    return arrays


def char_disjoint_split(manifest: pd.DataFrame, seed: int, test_ratio=0.2):
    """依「字」切分：每個字的所有樣本要嘛全在 train、要嘛全在 test。"""
    rng = np.random.default_rng(seed)
    chars = np.array(sorted(manifest["char"].unique()))
    rng.shuffle(chars)
    n_test = int(len(chars) * test_ratio)
    test_chars = set(chars[:n_test])
    is_test = manifest["char"].isin(test_chars).values
    return ~is_test, is_test


CLASSIFIERS = {
    "logreg": lambda: make_pipeline(StandardScaler(),
                                    LogisticRegression(max_iter=3000, C=1.0)),
    "svm_rbf": lambda: make_pipeline(StandardScaler(), SVC(C=10, gamma="scale")),
    "rf": lambda: RandomForestClassifier(n_estimators=400, n_jobs=-1),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()

    manifest = pd.read_csv(EXP / "manifest.csv")
    labels = sorted(manifest["label"].unique())
    y_all = manifest["label"].map({l: i for i, l in enumerate(labels)}).values
    feats = extract_features(manifest)
    feats["all"] = np.concatenate([feats[k] for k in FEATURE_SETS], axis=1)

    results = []
    cms = {}
    for seed in range(args.seeds):
        tr, te = char_disjoint_split(manifest, seed)
        for fname, X in feats.items():
            Xtr, Xte = np.nan_to_num(X[tr]), np.nan_to_num(X[te])
            for cname, mk in CLASSIFIERS.items():
                clf = mk()
                clf.fit(Xtr, y_all[tr])
                pred = clf.predict(Xte)
                acc = accuracy_score(y_all[te], pred)
                mf1 = f1_score(y_all[te], pred, average="macro")
                results.append({"seed": seed, "features": fname,
                                "clf": cname, "acc": acc, "macro_f1": mf1})
                if seed == 0:
                    cms[(fname, cname)] = confusion_matrix(y_all[te], pred)
                print(f"seed{seed} {fname:10s} {cname:8s} acc={acc:.4f} f1={mf1:.4f}")

    df = pd.DataFrame(results)
    df.to_csv(EXP / "results_classical.csv", index=False)
    summary = (df.groupby(["features", "clf"])[["acc", "macro_f1"]]
                 .agg(["mean", "std"]).round(4))
    print("\n===== 彙總（mean ± std over seeds）=====")
    print(summary.to_string())
    summary.to_csv(EXP / "results_classical_summary.csv")

    np.savez(EXP / "confusion_matrices.npz", labels=np.array(labels),
             **{f"{f}__{c}": m for (f, c), m in cms.items()})
    # 多數類基準
    maj = pd.Series(y_all).value_counts(normalize=True).iloc[0]
    print(f"\n多數類 baseline acc = {maj:.4f}；隨機 = {1/len(labels):.4f}")


if __name__ == "__main__":
    main()
