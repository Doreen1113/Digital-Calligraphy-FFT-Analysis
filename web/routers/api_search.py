"""
字元搜尋 API 路由

提供字元篩選、搜尋、統計、分頁瀏覽功能
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/filter")
async def filter_characters(
    min_count: int = Query(1, ge=1, le=4, description="最少書法家數量"),
    max_count: int = Query(4, ge=1, le=4, description="最多書法家數量"),
):
    """依書法家數量篩選字元"""
    from web.services.search_service import get_filtered_characters
    chars = get_filtered_characters(min_count, max_count)
    return {"total": len(chars), "characters": chars}


@router.get("/query")
async def search_query(
    q: str = Query(..., min_length=1, description="搜尋字串"),
):
    """搜尋字元"""
    from web.services.search_service import search
    results = search(q)
    return {"query": q, "total": len(results), "results": results}


@router.get("/stats")
async def search_stats():
    """取得字元統計資訊"""
    from web.services.search_service import get_stats
    return get_stats()


@router.get("/characters")
async def browse_characters(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(100, ge=10, le=500, description="每頁數量"),
    min_count: int = Query(1, ge=1, le=4, description="最少書法家數量"),
    max_count: int = Query(4, ge=1, le=4, description="最多書法家數量"),
):
    """分頁瀏覽字元"""
    from web.services.search_service import get_filtered_characters, paginate_characters
    chars = get_filtered_characters(min_count, max_count)
    return paginate_characters(chars, page, per_page)
