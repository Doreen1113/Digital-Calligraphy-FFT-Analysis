"""
字元搜尋服務

封裝 character_search 模組的搜尋與篩選功能
支援：依書法家數量篩選、依書法家篩選、排序（字頻序 / 筆畫序）
"""
import json
import sys
from functools import lru_cache
from typing import Dict, List, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_CHAR_DATA_FILE = PROJECT_ROOT / "data" / "index" / "char_data.json"


def _get_char_map() -> dict:
    """取得字元對應表"""
    from web.dependencies import get_character_index
    char_index = get_character_index()
    return char_index.get('character_map', {})


@lru_cache(maxsize=1)
def _load_char_data() -> dict:
    """載入字頻與筆畫數資料（只載入一次）"""
    if not _CHAR_DATA_FILE.exists():
        return {}
    try:
        with open(_CHAR_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _sort_chars(chars: List[str], sort_by: str) -> List[str]:
    """依指定方式排序字元列表"""
    char_data = _load_char_data()

    if sort_by == 'freq':
        # 字頻序：rank 小（常用）→ 大（罕見）
        return sorted(chars, key=lambda c: char_data.get(c, {}).get('freq_rank', 9999))
    elif sort_by == 'strokes_asc':
        # 筆畫序（少 → 多）
        return sorted(chars, key=lambda c: (char_data.get(c, {}).get('strokes', 999), c))
    elif sort_by == 'strokes_desc':
        # 筆畫序（多 → 少）
        return sorted(chars, key=lambda c: (-char_data.get(c, {}).get('strokes', 0), c))
    else:
        # 預設：Unicode 碼點序（原本行為）
        return sorted(chars)


def get_filtered_characters(
    min_count: int = 1,
    max_count: int = 99,
    sort_by: str = 'default',
    calligrapher: Optional[str] = None,
) -> List[str]:
    """依書法家數量（與可選的書法家名稱）篩選字元"""
    char_map = _get_char_map()
    result = []
    for char, cals in char_map.items():
        count = len(cals)
        if not (min_count <= count <= max_count):
            continue
        # 若有指定書法家，只保留該書法家擁有的字
        if calligrapher and calligrapher not in cals:
            continue
        result.append(char)
    return _sort_chars(result, sort_by)


def search(query: str) -> List[str]:
    """搜尋字元"""
    char_map = _get_char_map()
    results = []
    for char in query:
        if char in char_map:
            results.append(char)
    # 如果沒找到完全匹配，嘗試模糊搜尋
    if not results:
        try:
            from tools.analysis.character_search import search_characters
            results = search_characters(char_map, query)
        except ImportError:
            pass
    return results


def get_stats() -> Dict:
    """取得字元統計"""
    char_map = _get_char_map()
    total = len(char_map)

    # 依書法家數量分類（動態計算，不硬編碼上限）
    by_count = {}
    for char, cals in char_map.items():
        count = len(cals)
        by_count[count] = by_count.get(count, 0) + 1

    # 取得共有字
    from web.dependencies import get_character_index
    char_index = get_character_index()
    common = char_index.get('common_characters', [])

    return {
        "total_characters": total,
        "by_calligrapher_count": by_count,
        "common_characters_count": len(common),
        "common_percentage": round(len(common) / total * 100, 1) if total > 0 else 0,
    }


def paginate_characters(characters: List[str], page: int, per_page: int) -> Dict:
    """分頁"""
    total = len(characters)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "characters": characters[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
    }
