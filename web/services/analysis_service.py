"""
風格分析服務

提供 FFT 分析圖片、特徵說明、雷達圖數據、相似度數據
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional, List

PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_calligrapher_list() -> List[Dict]:
    """從 fonts_index.json 取得書法家列表"""
    fonts_index_path = PROJECT_ROOT / "data" / "index" / "fonts_index.json"

    calligraphers = []
    if fonts_index_path.exists():
        try:
            with open(fonts_index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cal_data = data.get('calligraphers', {})
            for key, info in cal_data.items():
                calligraphers.append({
                    'id': info.get('id', key),
                    'name': info.get('display_name', key),
                    'dynasty': info.get('dynasty', ''),
                    'style': info.get('style', ''),
                })
        except Exception:
            pass

    return calligraphers


def get_analysis_images() -> Dict:
    """檢查預生成的分析圖片是否存在，回傳 URL"""
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


# ------------------------------------------------------------------
# 特徵說明 — 面向觀眾的易懂版本
# ------------------------------------------------------------------
# feature_key → 技術定義 + 觀眾能理解的書法意義
_FEATURE_DESCRIPTIONS = {
    'low_freq': {
        'name': '結構穩定度',
        'name_en': 'Structural Stability',
        'description': '衡量字的整體骨架是否端正工整，來自傅立葉低頻能量。',
        'high_meaning': '字形骨架穩固、間架方正',
        'low_meaning': '字形較為自由靈動、不拘一格',
        'calligraphy_meaning': '歐體、柳體等楷書此項較高；行書草書較低',
    },
    'mid_freq': {
        'name': '筆畫變化度',
        'name_en': 'Stroke Variation',
        'description': '衡量筆畫粗細、轉折、提按的豐富程度，來自傅立葉中頻能量。',
        'high_meaning': '提按明顯、筆勢變化豐富',
        'low_meaning': '用筆均勻穩定、變化較少',
        'calligraphy_meaning': '顏真卿肥瘦對比大此項高；歐陽詢用筆較均勻此項低',
    },
    'high_freq': {
        'name': '細節豐富度',
        'name_en': 'Detail Richness',
        'description': '衡量飛白、毛邊、牽絲等細微筆觸的多寡，來自傅立葉高頻能量。',
        'high_meaning': '墨色層次多、有飛白與毛邊效果',
        'low_meaning': '線條光滑乾淨、邊緣整齊',
        'calligraphy_meaning': '碑帖中保留自然書寫質感的此項較高',
    },
    'centroid': {
        'name': '細節vs結構',
        'name_en': 'Detail-Structure Balance',
        'description': '頻譜能量重心偏向細節端還是結構端，反映整體風格取向。',
        'high_meaning': '重視細節表現（裝飾性強）',
        'low_meaning': '重視整體結構（骨架為主）',
        'calligraphy_meaning': '行草書重視細節此項高；楷書重視結構此項低',
    },
    'dc_ratio': {
        'name': '字形完整度',
        'name_en': 'Form Completeness',
        'description': '衡量字的輪廓是否渾然一體，來自直流分量與基頻之比。',
        'high_meaning': '筆畫連貫、字形渾然天成',
        'low_meaning': '筆畫獨立分明、結構清晰',
        'calligraphy_meaning': '沈尹默此項最高（筆畫連貫），歐陽詢較低（筆畫分明）',
    },
    'slope': {
        'name': '細節保留度',
        'name_en': 'Detail Preservation',
        'description': '高頻能量衰減的平緩程度，反映書寫細節是否被保留下來。',
        'high_meaning': '細膩筆觸完好保存、質感豐富',
        'low_meaning': '細節簡化明顯、線條概括',
        'calligraphy_meaning': '顏真卿此項最高（細節豐富），智永較低（線條簡潔）',
    },
    'hf_decay': {
        'name': '收筆乾淨度',
        'name_en': 'Stroke Ending Cleanness',
        'description': '高頻衰減速率——衡量筆觸收尾是否乾脆。',
        'high_meaning': '收筆果斷、筆觸延伸自然',
        'low_meaning': '收筆較為拘謹、速度較慢',
        'calligraphy_meaning': '沈尹默此項最高（行氣流暢），歐陽詢較低（收筆嚴謹）',
    },
}

_FEATURE_ORDER = ['low_freq', 'mid_freq', 'high_freq', 'centroid',
                  'dc_ratio', 'slope', 'hf_decay']


def get_feature_descriptions() -> Dict:
    """取得 7 個特徵的詳細說明（面向觀眾的易懂版本）"""
    return {
        "features": _FEATURE_DESCRIPTIONS,
        "feature_order": _FEATURE_ORDER,
    }


def get_radar_chart_data() -> Optional[Dict]:
    """
    取得雷達圖 JSON 數據

    優先讀取 data/index/style_features.json（由 analyze_styles.py 產生）
    """
    style_feat_path = PROJECT_ROOT / "data" / "index" / "style_features.json"

    if style_feat_path.exists():
        with open(style_feat_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    # 無真實數據 → 回傳 None（不再產生 demo 假數據）
    return None


def get_similarity_data() -> Optional[Dict]:
    """取得相似度矩陣數據"""
    sim_path = PROJECT_ROOT / "data" / "index" / "similarity_matrix.json"

    if sim_path.exists():
        with open(sim_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # 無真實數據 → 回傳 None
    return None
