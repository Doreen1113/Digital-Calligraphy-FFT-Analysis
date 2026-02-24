"""
字元搜尋服務

封裝 character_search 模組的搜尋與篩選功能
"""
import sys
from typing import Dict, List
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _get_char_map() -> dict:
    """取得字元對應表"""
    from web.dependencies import get_character_index
    char_index = get_character_index()
    return char_index.get('character_map', {})


def get_filtered_characters(min_count: int = 1, max_count: int = 99) -> List[str]:
    """依書法家數量篩選字元"""
    char_map = _get_char_map()
    result = []
    for char, cals in char_map.items():
        count = len(cals)
        if min_count <= count <= max_count:
            result.append(char)
    return sorted(result)


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
