"""
書法練字診斷 API

端點：
  GET  /api/score/calligraphers?char=天  → 取得某字的可用書法家清單
  POST /api/score/analyze               → 上傳圖片，與單一（或自動選定）書法家比對
  POST /api/score/analyze_all           → 上傳圖片，一次與全部有寫過該字的書法家比對並排序
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
    上傳手寫字圖片，與書法大師比對並產生分項量測與差異疊圖。

    回傳（不含單一總分——形態與結構是獨立維度，合成總分需要武斷權重）：
    - shape_score：整體形態相似度（0~1）
    - balance_score：結構平衡度（0~1）
    - balance_detail：左右/上下均衡細節
    - feedback：分項文字回饋
    - ref_cal_name：比對使用的書法家
    - ref_image_url：書法家參考圖 URL
    - diff_image：預先算好的差異疊圖（差異敏感度=0，即精確比對）
    - user_mask_image / ref_mask_image：重心對齊後的墨跡遮罩，供前端「差異敏感度」
      滑桿即時重繪疊圖，不用每次調整滑桿都重打一次 API
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
        raise HTTPException(status_code=500, detail=f"分析失敗：{e}")


@router.post("/analyze_all")
async def analyze_all(
    file: UploadFile = File(..., description="手寫字圖片（JPG/PNG/WebP/BMP，≤ 5 MB）"),
    char: str        = Form(..., min_length=1, max_length=1, description="所練的中文字"),
):
    """
    上傳一次圖片，與該字所有有寫過的書法家分別比對。

    回傳依形態相似度由高到低排序的清單，避免使用者每換一位書法家
    就要重新上傳圖片。

    回傳：{"char": ..., "results": [{shape_score, balance_score, ...}, ...]}
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
        from web.services.score_service import analyze_character_all
        result = await asyncio.to_thread(analyze_character_all, raw, char)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失敗：{e}")
