"""
網站統計 API 路由

提供頁面瀏覽次數與訪客統計
"""
import uuid
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()


@router.get("/overview")
async def get_overview():
    """取得網站統計概覽（總瀏覽次數、唯一訪客數）"""
    try:
        from web.services.stats_service import get_stats
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資料失敗：{e}")


@router.post("/visit")
async def record_visit(request: Request, response: Response):
    """記錄一次訪問（由頁面 JS 呼叫）"""
    try:
        from web.services.stats_service import record_page_view, record_visitor

        # 取得或建立訪客 cookie
        visitor_id = request.cookies.get("visitor_id")
        is_new = False
        if not visitor_id:
            visitor_id = str(uuid.uuid4())
            response.set_cookie(
                "visitor_id", visitor_id,
                max_age=365 * 24 * 3600,
                httponly=True,
                samesite="lax",
            )
            is_new = True

        # 記錄瀏覽與訪客
        referer = request.headers.get("referer", "")
        page = ""
        if referer:
            from urllib.parse import urlparse
            page = urlparse(referer).path

        record_page_view(page)
        if is_new or not request.cookies.get("visitor_id"):
            record_visitor(visitor_id)

        return {"ok": True, "is_new_visitor": is_new}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"記錄訪問失敗：{e}")
