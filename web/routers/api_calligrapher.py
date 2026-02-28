"""
書法家 API 路由

提供書法家資訊、統計數據、範例圖片、FFT 風格特徵等
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_style_features() -> dict:
    """載入 style_features.json 的 FFT 風格資料"""
    sf_path = PROJECT_ROOT / "data" / "index" / "style_features.json"
    if not sf_path.exists():
        return {}
    try:
        with open(sf_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_style_info(display_name: str, sf: dict) -> dict:
    """取得單一書法家的 FFT 風格摘要"""
    data = sf.get("data", {}).get(display_name)
    labels = sf.get("labels", [])
    feature_keys = sf.get("feature_keys", [])
    if not data or not labels:
        return {}

    vals = data if isinstance(data, list) else list(data.values())

    # 找最高和最低的特徵
    max_idx = max(range(len(vals)), key=lambda i: vals[i])
    min_idx = min(range(len(vals)), key=lambda i: vals[i])

    return {
        "feature_labels": labels,
        "feature_keys": feature_keys,
        "feature_values": vals,
        "strongest": {"label": labels[max_idx], "value": round(vals[max_idx], 3)},
        "weakest":  {"label": labels[min_idx], "value": round(vals[min_idx], 3)},
    }


@router.get("/list")
async def calligrapher_list():
    """取得所有書法家列表（含統計資訊 + FFT 風格摘要）"""
    from web.dependencies import get_calligrapher_list, get_fonts_index

    cals = get_calligrapher_list()
    fonts_index = get_fonts_index()
    fonts_data = fonts_index.get('calligraphers', {})
    sf = _load_style_features()

    result = []
    for cal in cals:
        book = cal.get('book', '')
        font_label = f"{cal['display_name']}·{book}" if book else cal['display_name']
        info = {
            "id": cal['id'],
            "name": cal['name'],
            "display_name": cal['display_name'],
            "book": book,
            "font_label": font_label,      # "顏真卿·多寶塔碑"（下拉選單 / checkbox 用）
            "dynasty": cal['dynasty'],
            "style": cal['style'],
            "total_chars": cal.get('total_chars', 0),
            "description": cal.get('description', ''),
        }
        # 從索引取得更詳細的統計
        if cal['name'] in fonts_data:
            idx_data = fonts_data[cal['name']]
            info['total_images'] = idx_data.get('total_images', 0)
            info['unique_characters'] = idx_data.get('unique_characters', 0)

        # FFT 風格摘要
        style_info = _get_style_info(cal['display_name'], sf)
        if style_info:
            info['style_features'] = style_info

        result.append(info)

    return {"calligraphers": result}


@router.get("/{cal_id}")
async def calligrapher_detail(cal_id: str):
    """取得單一書法家詳細資訊（含範例圖片）"""
    from web.dependencies import get_calligrapher_list, get_fonts_index
    import os

    cals = get_calligrapher_list()
    fonts_index = get_fonts_index()
    fonts_data = fonts_index.get('calligraphers', {})

    # 支援用 id 或 name 查詢
    cal = None
    for c in cals:
        if c['id'] == cal_id or c['name'] == cal_id:
            cal = c
            break

    if not cal:
        raise HTTPException(status_code=404, detail=f"找不到書法家: {cal_id}")

    book = cal.get('book', '')
    font_label = f"{cal['display_name']}·{book}" if book else cal['display_name']
    info = {
        "id": cal['id'],
        "name": cal['name'],
        "display_name": cal['display_name'],
        "book": book,
        "font_label": font_label,
        "dynasty": cal['dynasty'],
        "style": cal['style'],
        "total_chars": cal.get('total_chars', 0),
        "description": cal.get('description', ''),
    }

    # 從索引取得統計
    if cal['name'] in fonts_data:
        idx_data = fonts_data[cal['name']]
        info['total_images'] = idx_data.get('total_images', 0)
        info['unique_characters'] = idx_data.get('unique_characters', 0)

    # 取得範例圖片（前 12 張）
    image_dir = PROJECT_ROOT / cal['image_dir'].replace("./", "")
    sample_images = []
    if image_dir.exists():
        img_files = sorted([f for f in image_dir.iterdir()
                          if f.suffix.lower() in ('.png', '.jpg', '.jpeg')])[:12]
        for f in img_files:
            rel = f.relative_to(PROJECT_ROOT / "Fonts" / "my_fonts")
            sample_images.append(f"/fonts/{str(rel).replace(os.sep, '/')}")

    info['sample_images'] = sample_images

    # FFT 風格摘要
    sf = _load_style_features()
    style_info = _get_style_info(cal['display_name'], sf)
    if style_info:
        info['style_features'] = style_info

    return info
