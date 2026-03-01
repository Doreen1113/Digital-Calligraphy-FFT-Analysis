"""
書法練字評分 API

端點：
  GET  /api/score/calligraphers?char=天  → 取得某字的可用書法家清單
  POST /api/score/analyze               → 上傳圖片並評分
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

router = APIRouter()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
_MAX_SIZE = 5 * 1024 * 1024   # 5 MB


@router.get("/calligraphers")
async def get_calligraphers(
    char: str = Query(..., min_length=1, max_length=1, description="查詢的中文字"),
):
    """取得指定字的可用書法家清單（名稱 + 預覽圖 URL）"""
    try:
        from web.services.score_service import get_available_calligraphers
        cals = await asyncio.to_thread(get_available_calligraphers, char)
        return {"char": char, "calligraphers": cals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(..., description="手寫字圖片（JPG/PNG/WebP/BMP，≤ 5 MB）"),
    char: str        = Form(..., min_length=1, max_length=1, description="所練的中文字"),
    cal_name: Optional[str] = Form(None, description="指定書法家名稱（留空自動選）"),
):
    """
    上傳手寫字圖片，與書法大師比對並給予評分。

    回傳：
    - total_score：綜合分數（0~1）
    - shape_score：整體形態相似度（0~1）
    - balance_score：結構平衡度（0~1）
    - balance_detail：左右/上下均衡細節
    - feedback：文字回饋
    - ref_cal_name：比對使用的書法家
    - ref_image_url：書法家參考圖 URL
    """
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的圖片格式：{file.content_type}。請上傳 JPG/PNG/WebP/BMP",
        )

    raw = await file.read()
    if len(raw) > _MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"圖片超過 5 MB（目前 {len(raw) // 1024} KB）",
        )

    try:
        from web.services.score_service import analyze_character
        result = await asyncio.to_thread(
            analyze_character,
            raw,
            char,
            cal_name.strip() if cal_name and cal_name.strip() else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"評分失敗：{e}")
