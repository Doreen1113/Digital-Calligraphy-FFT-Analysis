"""
HTML 頁面路由

渲染 Jinja2 模板頁面
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/")
async def index(request: Request):
    """首頁：輸入一個字，看大師怎麼寫"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "輸入一個字，看大師怎麼寫",
        "active": "index",
        "page_desc": "輸入任一中文字，即時比較智永、沈尹默、顏真卿、趙孟頫、歐陽詢五位書法大師的筆法差異。",
    })


@router.get("/analysis")
async def analysis(request: Request):
    """風格分析頁：書法風格 DNA"""
    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "title": "書法風格 DNA",
        "active": "analysis",
        "page_desc": "以傅立葉描述子（FFT）量化分析書法風格特徵，呈現五位大師的風格 DNA 比對。",
    })


@router.get("/calligraphers")
async def calligraphers(request: Request):
    """書法家介紹頁"""
    return templates.TemplateResponse("calligraphers.html", {
        "request": request,
        "title": "認識書法家",
        "active": "calligraphers",
        "page_desc": "深入了解智永、沈尹默、顏真卿、趙孟頫、歐陽詢五位書法大師的生平與風格特色。",
    })


@router.get("/compare")
async def compare(request: Request):
    """批次比對頁"""
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "title": "批次比對",
        "active": "compare",
        "page_desc": "一次輸入多個文字，批次產生五位書法大師的對照圖，方便教學與研究使用。",
    })


@router.get("/explorer")
async def explorer(request: Request):
    """字元探索頁"""
    return templates.TemplateResponse("explorer.html", {
        "request": request,
        "title": "字元探索",
        "active": "explorer",
        "page_desc": "瀏覽全部可比對的書法字元，支援字頻序、筆畫序排列，依書法家篩選。",
    })


@router.get("/upload")
async def upload(request: Request):
    """上傳比對頁：上傳你的手寫字，與大師比一比"""
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "title": "上傳你的字，與大師比一比",
        "active": "upload",
        "page_desc": "上傳你手寫的中文字圖片，與智永、顏真卿等書法大師的版本並排比對。",
    })
