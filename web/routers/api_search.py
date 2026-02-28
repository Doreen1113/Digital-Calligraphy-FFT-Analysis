"""
字元搜尋 API 路由

提供字元篩選、搜尋、統計、分頁瀏覽功能
支援：排序（字頻序 / 筆畫序）、依書法家篩選、依部首篩選
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/filter")
async def filter_characters(
    min_count: int = Query(1, ge=1, description="最少書法家數量"),
    max_count: int = Query(99, ge=1, description="最多書法家數量"),
    sort_by: str = Query("default", description="排序方式：default / freq / strokes_asc / strokes_desc"),
    calligrapher: Optional[str] = Query(None, description="指定書法家（中文顯示名）"),
    radical: Optional[str] = Query(None, description="指定部首（如「水」「木」「心」）"),
):
    """依書法家數量（與可選條件）篩選字元"""
    from web.services.search_service import get_filtered_characters
    chars = get_filtered_characters(min_count, max_count, sort_by, calligrapher, radical)
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


@router.get("/radicals")
async def available_radicals():
    """取得所有可用部首及各部首字元數量"""
    from web.services.search_service import get_available_radicals
    radicals = get_available_radicals()
    return {"total": len(radicals), "radicals": radicals}


@router.get("/characters")
async def browse_characters(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(100, ge=10, le=500, description="每頁數量"),
    min_count: int = Query(1, ge=1, description="最少書法家數量"),
    max_count: int = Query(99, ge=1, description="最多書法家數量"),
    sort_by: str = Query("default", description="排序方式：default / freq / strokes_asc / strokes_desc"),
    calligrapher: Optional[str] = Query(None, description="指定書法家（中文顯示名）"),
    radical: Optional[str] = Query(None, description="指定部首（如「水」「木」「心」）"),
):
    """分頁瀏覽字元"""
    from web.services.search_service import get_filtered_characters, paginate_characters
    chars = get_filtered_characters(min_count, max_count, sort_by, calligrapher, radical)
    return paginate_characters(chars, page, per_page)
