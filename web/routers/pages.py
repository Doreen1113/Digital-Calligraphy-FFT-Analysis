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
    return templates.TemplateResponse(request, "about.html", {
        "title": "關於墨跡習字",
        "active": "about",
        "page_desc": "墨跡習字 — 用傅立葉描述子分析書法風格，比對大師筆法、上傳練習作品取得筆劃差異診斷。",
        "page_keywords": "墨跡習字,書法學習,書法比對,FFT,關於,成立初衷",
    })


@router.get("/")
async def index_redirect():
    """首頁：重導向至關於頁"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/about", status_code=302)


@router.get("/analysis")
async def analysis(request: Request):
    """風格分析頁：書法風格特徵探索"""
    return templates.TemplateResponse(request, "analysis.html", {
        "title": "書法風格特徵探索",
        "active": "analysis",
        "page_desc": "以傅立葉描述子（FFT）量化分析書法風格特徵，並公開統計檢定結果，誠實呈現分析的可信度。",
        "page_keywords": "書法風格分析,傅立葉描述子,FFT,書法特徵,風格比較,書法科學",
    })


@router.get("/analysis/methodology")
async def analysis_methodology(request: Request):
    """風格分析方法論頁：資料樣本、共同字方法、統計檢定細節、7 維特徵解讀"""
    return templates.TemplateResponse(request, "methodology.html", {
        "title": "分析方法與統計檢定",
        "active": "analysis",
        "page_desc": "書法風格特徵探索頁面的完整方法論：資料樣本、共同字比較法、ANOVA 統計檢定與 7 維特徵解讀。",
        "page_keywords": "書法風格分析方法論,ANOVA,統計檢定,傅立葉描述子,FFT",
    })


@router.get("/calligraphers")
async def calligraphers(request: Request):
    """書法家介紹頁"""
    return templates.TemplateResponse(request, "calligraphers.html", {
        "title": "認識書法家",
        "active": "calligraphers",
        "page_desc": "深入了解智永、沈尹默、顏真卿、趙孟頫、歐陽詢五位書法大師的生平與風格特色。",
        "page_keywords": "書法家介紹,智永,顏真卿,歐陽詢,趙孟頫,王羲之,書法大師,書法歷史",
    })


@router.get("/compare")
async def compare(request: Request):
    """批次比對頁"""
    return templates.TemplateResponse(request, "compare.html", {
        "title": "批次比對",
        "active": "compare",
        "page_desc": "一次輸入多個文字，批次產生五位書法大師的對照圖，方便教學與研究使用。",
        "page_keywords": "批次書法比對,漢字對照,書法教學,毛筆字練習,書法範本",
    })


@router.get("/explorer")
async def explorer(request: Request):
    """字元探索頁"""
    return templates.TemplateResponse(request, "explorer.html", {
        "title": "字元探索",
        "active": "explorer",
        "page_desc": "瀏覽全部可比對的書法字元，支援字頻序、筆畫序排列，依書法家篩選。",
        "page_keywords": "漢字探索,書法字庫,字元查詢,筆畫查詢,部首查詢,書法字典",
    })


@router.get("/stroke-order")
async def stroke_order(request: Request):
    """筆順動畫頁：輸入漢字，播放標準筆順動畫"""
    return templates.TemplateResponse(request, "stroke_order.html", {
        "title": "筆順動畫",
        "active": "stroke-order",
        "page_desc": "輸入任一漢字，即時播放標準筆順動畫，幫助書法初學者掌握正確書寫順序。",
        "page_keywords": "筆順,漢字筆順,書寫順序,書法學習,筆順動畫",
    })


@router.get("/upload")
async def upload_redirect(request: Request):
    """舊版 /upload 頁面 → 重新導向至 /score（上傳 & 評分）"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/score", status_code=301)


@router.get("/score")
async def score(request: Request):
    """筆劃診斷頁：上傳手寫字，與大師比一比，取得筆劃差異圖與分項量測"""
    return templates.TemplateResponse(request, "score.html", {
        "title": "筆劃診斷",
        "active": "score",
        "page_desc": "上傳你手寫的中文字圖片，與書法大師版本比對，取得形態相似度與結構平衡度量測數據及筆劃差異標示圖，適合書法初學者自我練習。",
        "page_keywords": "書法診斷,練字,手寫漢字,書法練習,書法比對,書法初學者,形態相似度,結構平衡",
    })
