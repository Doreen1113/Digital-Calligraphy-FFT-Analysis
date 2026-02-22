"""
書法家 API 路由

提供書法家資訊、統計數據、範例圖片等
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path

router = APIRouter()
PROJECT_ROOT = Path(__file__).parent.parent.parent


@router.get("/list")
async def calligrapher_list():
    """取得所有書法家列表（含統計資訊）"""
    from web.dependencies import get_calligrapher_list, get_fonts_index

    cals = get_calligrapher_list()
    fonts_index = get_fonts_index()
    fonts_data = fonts_index.get('calligraphers', {})

    result = []
    for cal in cals:
        info = {
            "id": cal['id'],
            "name": cal['name'],
            "display_name": cal['display_name'],
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

    info = {
        "id": cal['id'],
        "name": cal['name'],
        "display_name": cal['display_name'],
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

    return info
