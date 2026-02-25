"""
書法風格分析系統 - FastAPI 應用程式

提供 Web API 和前端頁面服務
"""
import os
import sys
import uuid
from pathlib import Path

# 確保專案根目錄在 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 設定 matplotlib 非互動模式
import matplotlib
matplotlib.use('Agg')

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# === 建立 FastAPI 應用 ===
app = FastAPI(
    title="書法風格分析系統",
    description="使用傅立葉描述子分析書法風格，支援同字比對與風格查詢",
    version="2.0",
)

# === CORS 中介軟體（允許前端跨域存取）===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 掛載靜態檔案 ===

# CSS、JS、前端圖片
static_dir = PROJECT_ROOT / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 分析輸出圖片（比對結果、雷達圖等）
output_dir = PROJECT_ROOT / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

# 書法原圖（2809 張）
fonts_dir = PROJECT_ROOT / "Fonts" / "my_fonts"
if fonts_dir.exists():
    app.mount("/fonts", StaticFiles(directory=str(fonts_dir)), name="fonts")

# === 訪客統計中介軟體 ===
_SKIP_PREFIXES = ('/api', '/static', '/fonts', '/output', '/docs', '/redoc', '/openapi', '/favicon')

@app.middleware("http")
async def stats_middleware(request: Request, call_next):
    """自動記錄 HTML 頁面瀏覽次數與唯一訪客"""
    response = await call_next(request)
    path = request.url.path
    # 只統計 HTML 頁面請求
    if not any(path.startswith(p) for p in _SKIP_PREFIXES):
        try:
            from web.services.stats_service import record_page_view, record_visitor
            record_page_view(path)
            visitor_id = request.cookies.get("visitor_id")
            if not visitor_id:
                visitor_id = str(uuid.uuid4())
                response.set_cookie(
                    "visitor_id", visitor_id,
                    max_age=365 * 24 * 3600,
                    httponly=True,
                    samesite="lax",
                )
                record_visitor(visitor_id)
            else:
                record_visitor(visitor_id)
        except Exception:
            pass
    return response


# === 註冊路由 ===
from web.routers import pages, api_character, api_analysis, api_search, api_calligrapher, api_stats

app.include_router(pages.router)
app.include_router(api_character.router, prefix="/api/character", tags=["character"])
app.include_router(api_analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(api_search.router, prefix="/api/search", tags=["search"])
app.include_router(api_calligrapher.router, prefix="/api/calligrapher", tags=["calligrapher"])
app.include_router(api_stats.router, prefix="/api/stats", tags=["stats"])


# === 啟動事件 ===
@app.on_event("startup")
async def startup_event():
    """伺服器啟動時驗證必要檔案"""
    from web.dependencies import validate_environment
    validate_environment()
