"""
字元比對 API 路由

提供單字比對、批次比對、字元查詢等功能
"""
import asyncio
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

router = APIRouter()


@router.get("/compare")
async def compare_character(
    char: str = Query(..., min_length=1, max_length=1, description="單一中文字元"),
    calligraphers: Optional[List[str]] = Query(None, description="書法家顯示名稱列表"),
):
    """比對單一字元 - 回傳比對圖片 URL"""
    from web.services.character_service import compare_single
    result = await asyncio.to_thread(compare_single, char, calligraphers)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/available")
async def available_characters():
    """取得所有可比對字元"""
    from web.dependencies import get_character_index
    char_index = get_character_index()
    chars = sorted(char_index.get('character_map', {}).keys())
    return {"total": len(chars), "characters": chars}


@router.get("/common")
async def common_characters():
    """取得共有字（4 位書法家都有的字）"""
    from web.dependencies import get_character_index
    char_index = get_character_index()
    common = char_index.get('common_characters', [])
    return {"total": len(common), "characters": common}


@router.get("/info/{char}")
async def character_info(char: str):
    """取得單一字元的詳細資訊（各書法家的圖片路徑、筆畫數、字頻）"""
    import json
    from pathlib import Path
    from web.dependencies import get_character_index, get_name_font_label_dict

    char_index = get_character_index()
    char_map   = char_index.get('character_map', {})

    if char not in char_map:
        raise HTTPException(status_code=404, detail=f"字元 '{char}' 不在索引中")

    # 讀取筆畫 / 字頻資料
    char_data_file = Path(__file__).parent.parent.parent / "data" / "index" / "char_data.json"
    char_extra = {}
    if char_data_file.exists():
        try:
            with open(char_data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            char_extra = all_data.get(char, {})
        except Exception:
            pass

    label_map = get_name_font_label_dict()

    # key = "書法家·字帖"（同一書法家多本字帖各自有獨立 key，不覆蓋）
    calligraphers_data = {}
    for cal_name, instances in char_map[char].items():
        font_label = label_map.get(cal_name, cal_name)  # e.g. "顏真卿·多寶塔碑"
        images = []
        for inst in instances:
            img_path = inst.get('image_path', '')
            norm = img_path.replace("\\", "/")
            # 支援 Windows 絕對路徑（C:/My_Project/.../Fonts/my_fonts/...）
            if "Fonts/my_fonts/" in norm:
                rel = norm.split("Fonts/my_fonts/", 1)[-1]
            else:
                rel = norm.lstrip("./")
            images.append({
                "filename": inst.get('filename', ''),
                "image_url": f"/fonts/{rel}",
                "book":    inst.get('book', ''),
                "font_id": inst.get('font_id', ''),
            })
        calligraphers_data[font_label] = images

    freq_rank = char_extra.get('freq_rank', None)
    return {
        "character":  char,
        "calligraphers": calligraphers_data,
        "count":      len(calligraphers_data),
        "strokes":    char_extra.get('strokes', None),
        "freq_rank":  freq_rank if freq_rank and freq_rank < 9999 else None,
        "radical":    char_extra.get('radical', None),
    }


@router.get("/ink-reveal")
async def ink_reveal(path: str = Query(..., description="相對 Fonts/my_fonts 的圖片路徑，例如 07/char_0001.png")):
    """
    把一張書法家真跡圖片拆成獨立墨跡區塊，回傳可播放漸進浮現動畫的 SVG。

    這不是真正的筆順辨識——連在一起的筆畫會被當成同一塊一起出現，順序也只是
    由上到下、由左到右的閱讀順序，不保證是實際書寫順序。見 src/core/ink_reveal.py。
    """
    import asyncio
    import hashlib
    from pathlib import Path
    from web.dependencies import get_project_root

    root = Path(get_project_root())
    fonts_dir = (root / "Fonts" / "my_fonts").resolve()

    # 防止路徑穿越：確保解析後的路徑仍在 fonts_dir 底下
    img_path = (fonts_dir / path).resolve()
    if fonts_dir not in img_path.parents or not img_path.exists():
        raise HTTPException(status_code=404, detail="找不到圖片")

    cache_dir = root / "output" / "ink_reveal_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(str(img_path).encode("utf-8")).hexdigest()
    cache_file = cache_dir / f"{cache_key}.svg"

    if cache_file.exists():
        return {"svg": cache_file.read_text(encoding="utf-8")}

    from src.core.ink_reveal import generate_ink_reveal_svg
    result = await asyncio.to_thread(generate_ink_reveal_svg, str(img_path))
    if result is None:
        raise HTTPException(status_code=500, detail="圖片解析失敗")

    cache_file.write_text(result["svg"], encoding="utf-8")
    return {"svg": result["svg"], "piece_count": result["piece_count"]}


@router.post("/batch")
async def batch_compare(body: dict):
    """批次比對多個字元 - 返回每個字元的獨立圖片"""
    import asyncio
    from web.services.character_service import compare_single, get_character_images

    characters = body.get("characters", "")
    selected = body.get("calligraphers", None)
    sort_mode = body.get("sort_mode", "character")  # "character" or "calligrapher"

    if not characters:
        raise HTTPException(status_code=400, detail="請輸入至少一個字元")

    # 收集每個字元的圖片資訊
    results = []
    for char in characters:
        if ord(char) >= 0x4E00 and ord(char) <= 0x9FFF:  # CJK 範圍
            img_data = await asyncio.to_thread(get_character_images, char, selected)
            results.append({"character": char, **img_data})

    success = sum(1 for r in results if "error" not in r)
    return {
        "results": results,
        "success_count": success,
        "total": len(characters),
        "sort_mode": sort_mode
    }
