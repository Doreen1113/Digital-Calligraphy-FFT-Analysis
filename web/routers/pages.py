"""
HTML 頁面路由

渲染 Jinja2 模板頁面
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/about")
async def about(request: Request):
    """關於頁：網站介紹、成立初衷、聯絡資訊"""
    return templates.TemplateResponse("about.html", {
        "request": request,
        "title": "關於墨跡習字",
        "active": "about",
        "page_desc": "墨跡習字 — 用數位科技量化書法風格，讓學習者直觀比較大師筆法、了解練習進度。",
        "page_keywords": "墨跡習字,書法學習,書法比對,FFT,關於,成立初衷",
    })


@router.get("/")
async def index(request: Request):
    """首頁：輸入一個字，看大師怎麼寫"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "輸入一個字，看大師怎麼寫",
        "active": "index",
        "page_desc": "輸入任一中文字，即時比較智永、沈尹默、顏真卿、趙孟頫、歐陽詢五位書法大師的筆法差異。",
        "page_keywords": "書法比對,漢字,毛筆字,楷書,行書,王羲之,顏真卿,書法教學",
    })


@router.get("/analysis")
async def analysis(request: Request):
    """風格分析頁：書法風格 DNA"""
    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "title": "書法風格 DNA",
        "active": "analysis",
        "page_desc": "以傅立葉描述子（FFT）量化分析書法風格特徵，呈現五位大師的風格 DNA 比對。",
        "page_keywords": "書法風格分析,傅立葉描述子,FFT,書法特徵,風格比較,書法科學",
    })


@router.get("/calligraphers")
async def calligraphers(request: Request):
    """書法家介紹頁"""
    return templates.TemplateResponse("calligraphers.html", {
        "request": request,
        "title": "認識書法家",
        "active": "calligraphers",
        "page_desc": "深入了解智永、沈尹默、顏真卿、趙孟頫、歐陽詢五位書法大師的生平與風格特色。",
        "page_keywords": "書法家介紹,智永,顏真卿,歐陽詢,趙孟頫,王羲之,書法大師,書法歷史",
    })


@router.get("/compare")
async def compare(request: Request):
    """批次比對頁"""
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "title": "批次比對",
        "active": "compare",
        "page_desc": "一次輸入多個文字，批次產生五位書法大師的對照圖，方便教學與研究使用。",
        "page_keywords": "批次書法比對,漢字對照,書法教學,毛筆字練習,書法範本",
    })


@router.get("/explorer")
async def explorer(request: Request):
    """字元探索頁"""
    return templates.TemplateResponse("explorer.html", {
        "request": request,
        "title": "字元探索",
        "active": "explorer",
        "page_desc": "瀏覽全部可比對的書法字元，支援字頻序、筆畫序排列，依書法家篩選。",
        "page_keywords": "漢字探索,書法字庫,字元查詢,筆畫查詢,部首查詢,書法字典",
    })


@router.get("/upload")
async def upload_redirect(request: Request):
    """舊版 /upload 頁面 → 重新導向至 /score（上傳 & 評分）"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/score", status_code=301)


@router.get("/score")
async def score(request: Request):
    """練字評分頁：上傳手寫字，與大師比一比並獲得評分"""
    return templates.TemplateResponse("score.html", {
        "request": request,
        "title": "練字評分",
        "active": "score",
        "page_desc": "上傳你手寫的中文字圖片，與書法大師版本比對，獲得整體形態相似度與結構平衡度評分，適合書法初學者自我練習。",
        "page_keywords": "書法評分,練字,手寫漢字,書法練習,書法比對,書法初學者,形態相似度,結構平衡",
    })
