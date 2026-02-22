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
    })


@router.get("/analysis")
async def analysis(request: Request):
    """風格分析頁：書法風格 DNA"""
    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "title": "書法風格 DNA",
        "active": "analysis",
    })


@router.get("/calligraphers")
async def calligraphers(request: Request):
    """書法家介紹頁"""
    return templates.TemplateResponse("calligraphers.html", {
        "request": request,
        "title": "認識書法家",
        "active": "calligraphers",
    })


@router.get("/compare")
async def compare(request: Request):
    """批次比對頁"""
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "title": "批次比對",
        "active": "compare",
    })


@router.get("/explorer")
async def explorer(request: Request):
    """字元探索頁"""
    return templates.TemplateResponse("explorer.html", {
        "request": request,
        "title": "字元探索",
        "active": "explorer",
    })
