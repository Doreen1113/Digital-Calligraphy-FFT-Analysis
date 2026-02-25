"""
網站統計服務

記錄頁面瀏覽次數與唯一訪客數，儲存於 data/stats.json
"""
import json
import threading
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
STATS_FILE = PROJECT_ROOT / "data" / "stats.json"

_lock = threading.Lock()


def _load_stats() -> dict:
    """從檔案讀取統計資料"""
    if not STATS_FILE.exists():
        return {"total_views": 0, "unique_visitors": 0, "visitor_ids": []}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"total_views": 0, "unique_visitors": 0, "visitor_ids": []}


def _save_stats(stats: dict):
    """將統計資料寫回檔案"""
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def record_page_view(page: str = ""):
    """記錄一次頁面瀏覽"""
    with _lock:
        stats = _load_stats()
        stats["total_views"] = stats.get("total_views", 0) + 1
        # 按頁面分類統計
        page_views = stats.get("page_views", {})
        page_key = page.strip("/") or "home"
        page_views[page_key] = page_views.get(page_key, 0) + 1
        stats["page_views"] = page_views
        _save_stats(stats)


def record_visitor(visitor_id: str) -> bool:
    """記錄唯一訪客；若為新訪客回傳 True"""
    with _lock:
        stats = _load_stats()
        visitor_ids = set(stats.get("visitor_ids", []))
        is_new = visitor_id not in visitor_ids
        if is_new:
            visitor_ids.add(visitor_id)
            stats["visitor_ids"] = list(visitor_ids)
            stats["unique_visitors"] = len(visitor_ids)
            _save_stats(stats)
        return is_new


def get_stats() -> dict:
    """取得統計摘要"""
    stats = _load_stats()
    return {
        "total_views": stats.get("total_views", 0),
        "unique_visitors": stats.get("unique_visitors", 0),
    }
