"""單字影像的特徵抽取：頻域輪廓描述子、頻譜統計特徵、Hu 矩。

三組特徵刻意對應三種「可解釋性層次」：
  fd        — 輪廓傅立葉描述子（旋轉/起點/縮放不變的振幅譜），描述「筆畫邊界的形狀節奏」
  spectral7 — 平台原本的 7 個頻譜統計量（低/中/高頻能量、質心、DC比、斜率、衰減）
  hu        — Hu 矩（整體形狀不變量），作為非頻域的傳統對照組
"""
from __future__ import annotations

import cv2
import numpy as np

# ── 前處理 ───────────────────────────────────────────────────────────────────

def binarize(img: np.ndarray) -> np.ndarray:
    """轉為墨跡=255、背景=0 的二值圖，並裁切置中到 256×256。"""
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 邊緣多數為亮 → 白底黑字 → 反轉成墨跡為前景
    edge = np.concatenate([bw[0, :], bw[-1, :], bw[:, 0], bw[:, -1]])
    ink = 255 - bw if edge.mean() > 127 else bw

    ys, xs = np.nonzero(ink)
    if len(ys) == 0:
        return np.zeros((256, 256), np.uint8)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = ink[y0:y1 + 1, x0:x1 + 1]
    h, w = crop.shape
    side = max(h, w)
    pad = np.zeros((side, side), np.uint8)
    pad[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = crop
    return cv2.resize(pad, (256, 256), interpolation=cv2.INTER_AREA)


def contours_of(ink: np.ndarray, min_len: int = 32, max_contours: int = 8):
    """取墨跡的輪廓（外輪廓＋內洞），依周長排序取前 max_contours 條。"""
    cnts, _ = cv2.findContours(ink, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    cnts = [c[:, 0, :].astype(np.float64) for c in cnts if len(c) >= min_len]
    cnts.sort(key=len, reverse=True)
    return cnts[:max_contours]


# ── 特徵 1：輪廓傅立葉描述子 ─────────────────────────────────────────────────

def fourier_descriptor(cnt: np.ndarray, n_coeffs: int = 20, n_resample: int = 256) -> np.ndarray:
    """單一封閉輪廓的正規化傅立葉描述子（振幅譜）。

    - 等弧長重新取樣 n_resample 點：消除取樣密度差異
    - 去掉 DC（平移不變）、除以 |c_1|（縮放不變）、取振幅（旋轉/起點不變）
    - 回傳頻率 ±1..±n_coeffs 的振幅，共 2*n_coeffs 維（c_1 恆為 1，保留作 sanity）
    """
    d = np.diff(cnt, axis=0, append=cnt[:1])
    seglen = np.hypot(d[:, 0], d[:, 1])
    arc = np.concatenate([[0], np.cumsum(seglen)])[:-1]
    total = arc[-1] + seglen[-1]
    if total <= 0:
        return np.zeros(2 * n_coeffs)
    t = np.linspace(0, total, n_resample, endpoint=False)
    x = np.interp(t, arc, cnt[:, 0], period=total)
    y = np.interp(t, arc, cnt[:, 1], period=total)
    z = x + 1j * y
    Z = np.fft.fft(z) / n_resample
    # 頻率 +1..+n 與 -1..-n
    pos = Z[1:n_coeffs + 1]
    neg = Z[-1:-n_coeffs - 1:-1]
    scale = max(abs(Z[1]), abs(Z[-1]), 1e-12)
    return np.concatenate([np.abs(pos), np.abs(neg)]) / scale


def fd_features(ink: np.ndarray, n_coeffs: int = 20) -> np.ndarray:
    """整字的 FD 特徵：各輪廓描述子以周長加權平均 ＋ 逐維標準差 ＋ 輪廓數量統計。"""
    cnts = contours_of(ink)
    if not cnts:
        return np.zeros(4 * n_coeffs + 2)
    descs = np.array([fourier_descriptor(c, n_coeffs) for c in cnts])
    w = np.array([len(c) for c in cnts], dtype=np.float64)
    w /= w.sum()
    mean = (descs * w[:, None]).sum(axis=0)
    std = descs.std(axis=0) if len(descs) > 1 else np.zeros_like(mean)
    extra = np.array([len(cnts), np.log1p(sum(len(c) for c in cnts))])
    return np.concatenate([mean, std, extra])


# ── 特徵 2：平台原本的 7 個頻譜統計量（逐輪廓計算後平均）───────────────────────

def spectral7(ink: np.ndarray, target_len: int = 50) -> np.ndarray:
    cnts = contours_of(ink)
    feats = []
    for cnt in cnts:
        z = (cnt[:, 0] - cnt[:, 0].mean()) + 1j * (cnt[:, 1] - cnt[:, 1].mean())
        amps = np.abs(np.fft.fft(z)) / len(z)
        if len(amps) < target_len:
            continue
        a = np.maximum(amps[:target_len], 1e-10)
        te = np.sum(a ** 2) + 1e-10
        low, mid, high = np.sum(a[:5] ** 2) / te, np.sum(a[5:15] ** 2) / te, np.sum(a[15:] ** 2) / te
        freqs = np.arange(target_len, dtype=np.float64)
        centroid = np.sum(freqs * a) / (np.sum(a) + 1e-10)
        dc_fund = a[0] / (a[1] + 1e-10)
        slope = abs(np.polyfit(freqs, np.log1p(a), 1)[0])
        decay = np.mean(a[10:20]) / a[1] if a[1] > 1e-10 else 0.0
        feats.append([low, mid, high, centroid / target_len, dc_fund, slope, decay])
    return np.mean(feats, axis=0) if feats else np.zeros(7)


# ── 特徵 3：Hu 矩 ────────────────────────────────────────────────────────────

def hu_features(ink: np.ndarray) -> np.ndarray:
    m = cv2.moments(ink, binaryImage=True)
    hu = cv2.HuMoments(m).flatten()
    return np.sign(hu) * np.log10(np.abs(hu) + 1e-30)


# ── 匯總 ─────────────────────────────────────────────────────────────────────

FEATURE_SETS = {
    "fd": lambda ink: fd_features(ink),
    "spectral7": spectral7,
    "hu": hu_features,
}


def extract_all(img: np.ndarray) -> dict[str, np.ndarray]:
    ink = binarize(img)
    return {name: fn(ink) for name, fn in FEATURE_SETS.items()}
