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
    """取得單一字元的詳細資訊（各書法家的圖片路徑）"""
    from web.dependencies import get_character_index, get_name_display_dict
    char_index = get_character_index()
    char_map = char_index.get('character_map', {})
    name_map = get_name_display_dict()

    if char not in char_map:
        raise HTTPException(status_code=404, detail=f"字元 '{char}' 不在索引中")

    calligraphers_data = {}
    for cal_name, instances in char_map[char].items():
        display = name_map.get(cal_name, cal_name)
        images = []
        for inst in instances:
            # 將檔案路徑轉為 URL
            img_path = inst.get('image_path', '')
            rel = img_path.replace("\\", "/").replace("./Fonts/my_fonts/", "")
            images.append({
                "filename": inst.get('filename', ''),
                "image_url": f"/fonts/{rel}",
            })
        calligraphers_data[display] = images

    return {
        "character": char,
        "calligraphers": calligraphers_data,
        "count": len(calligraphers_data),
    }


@router.post("/batch")
async def batch_compare(body: dict):
    """批次比對多個字元"""
    import asyncio
    from web.services.character_service import compare_single

    characters = body.get("characters", "")
    selected = body.get("calligraphers", None)

    if not characters:
        raise HTTPException(status_code=400, detail="請輸入至少一個字元")

    results = []
    for char in characters:
        if ord(char) >= 0x4E00 and ord(char) <= 0x9FFF:  # CJK 範圍
            r = await asyncio.to_thread(compare_single, char, selected)
            results.append({"character": char, **r})

    success = sum(1 for r in results if "error" not in r)
    return {"results": results, "success_count": success, "total": len(characters)}
