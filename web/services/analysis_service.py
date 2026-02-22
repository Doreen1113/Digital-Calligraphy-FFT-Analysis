"""
風格分析服務

提供 FFT 分析圖片、特徵說明、雷達圖數據、相似度數據
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_analysis_images() -> Dict:
    """
    檢查預生成的分析圖片是否存在，回傳 URL

    Returns:
        dict: 各圖片的 URL 或 None
    """
    output_dir = PROJECT_ROOT / "output"
    image_files = {
        "report_image": "style_analysis_report.png",
        "radar_image": "style_radar_chart.png",
        "similarity_image": "similarity_matrix.png",
        "bars_image": "feature_comparison_bars.png",
        "explanation_image": "feature_explanation.png",
    }

    result = {}
    all_exist = True
    for key, filename in image_files.items():
        path = output_dir / filename
        if path.exists():
            result[key] = f"/output/{filename}"
        else:
            result[key] = None
            all_exist = False

    result["generated"] = all_exist
    return result


def get_feature_descriptions() -> Dict:
    """取得 7 個 FFT 特徵的詳細說明"""
    try:
        from src.analysis.visualization import FEATURE_DESCRIPTIONS, FEATURE_ORDER
        return {
            "features": FEATURE_DESCRIPTIONS,
            "feature_order": FEATURE_ORDER,
        }
    except ImportError:
        return {
            "features": {},
            "feature_order": [],
            "error": "無法載入特徵說明模組",
        }


def get_radar_chart_data() -> Optional[Dict]:
    """
    取得雷達圖 JSON 數據

    優先讀取 data/index/style_features.json
    """
    style_feat_path = PROJECT_ROOT / "data" / "index" / "style_features.json"

    if style_feat_path.exists():
        with open(style_feat_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    # 嘗試從 style_data.csv 讀取
    csv_path = PROJECT_ROOT / "output" / "style_data.csv"
    if csv_path.exists():
        try:
            import pandas as pd
            import numpy as np
            df = pd.read_csv(csv_path, index_col=0)

            from src.analysis.visualization import FEATURE_DESCRIPTIONS, FEATURE_ORDER
            feature_names = [FEATURE_DESCRIPTIONS[f]['name'] for f in FEATURE_ORDER]

            # 正規化到 0-1
            calligraphers = list(df.columns)
            raw_data = {}
            normalized_data = {}

            for cal in calligraphers:
                raw_data[cal] = df[cal].tolist()

            # 正規化
            all_values = df.values
            for i, cal in enumerate(calligraphers):
                col = all_values[:, i] if i < all_values.shape[1] else all_values[:, 0]
                min_vals = all_values.min(axis=1)
                max_vals = all_values.max(axis=1)
                ranges = max_vals - min_vals
                ranges[ranges == 0] = 1
                normalized = (col - min_vals) / ranges
                normalized_data[cal] = normalized.tolist()

            return {
                "calligraphers": calligraphers,
                "features": feature_names,
                "raw_data": raw_data,
                "normalized_data": normalized_data,
            }
        except Exception:
            pass

    return None


def get_similarity_data() -> Optional[Dict]:
    """取得相似度矩陣數據"""
    sim_path = PROJECT_ROOT / "data" / "index" / "similarity_matrix.json"

    if sim_path.exists():
        with open(sim_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return None
