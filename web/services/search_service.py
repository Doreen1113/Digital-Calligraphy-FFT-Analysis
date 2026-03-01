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
    radical: Optional[str] = None,
) -> List[str]:
    """依書法家數量（與可選的書法家名稱、部首）篩選字元"""
    from web.dependencies import get_name_font_label_dict
    char_map = _get_char_map()
    char_data = _load_char_data() if radical else {}
    label_map = get_name_font_label_dict() if calligrapher else {}

    result = []
    for char, cals in char_map.items():
        count = len(cals)
        if not (min_count <= count <= max_count):
            continue
        # 若有指定書法家，用 font_label 萃取 display_name 比對（支援多本字帖 + _XX 新格式）
        if calligrapher:
            char_display_names = set()
            for cal_name in cals.keys():
                font_label = label_map.get(cal_name, cal_name)
                display_name = font_label.split('·')[0] if '·' in font_label else font_label
                char_display_names.add(display_name)
            if calligrapher not in char_display_names:
                continue
        # 若有指定部首，只保留該部首的字
        if radical and char_data.get(char, {}).get('radical', '') != radical:
            continue
        result.append(char)
    return _sort_chars(result, sort_by)


@lru_cache(maxsize=1)
def _build_pinyin_index() -> dict:
    """建立拼音 → 字元列表的反查索引（啟動後只建立一次）"""
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return {}

    char_map = _get_char_map()
    index: dict = {}   # "tian" → ["天", ...]
    for char in char_map:
        try:
            py = lazy_pinyin(char)[0].lower()   # 無聲調拼音
            if py not in index:
                index[py] = []
            index[py].append(char)
        except Exception:
            pass
    return index


def search(query: str) -> List[str]:
    """搜尋字元

    支援：
    - 直接輸入漢字（精確）
    - 拼音搜尋（如 "tian" 找「天」）
    """
    query = query.strip()
    char_map = _get_char_map()

    # 1. 直接匹配漢字
    results = [c for c in query if c in char_map]
    if results:
        return results

    # 2. 拼音搜尋（只含 a-z 的輸入視為拼音）
    if query.isascii() and query.isalpha():
        pinyin_index = _build_pinyin_index()
        q_lower = query.lower()
        # 精確拼音
        if q_lower in pinyin_index:
            return pinyin_index[q_lower]
        # 前綴拼音（e.g. "tia" 找 "tian"）
        prefix_matches = []
        for py, chars in pinyin_index.items():
            if py.startswith(q_lower):
                prefix_matches.extend(chars)
        if prefix_matches:
            return list(dict.fromkeys(prefix_matches))  # 去重保序

    return []


def get_available_radicals() -> List[Dict]:
    """取得所有可用的部首及其字數（只返回在資料集中實際出現的部首）"""
    char_map = _get_char_map()
    char_data = _load_char_data()
    radical_count: Dict[str, int] = {}
    for char in char_map:
        rad = char_data.get(char, {}).get('radical', '')
        if rad:
            radical_count[rad] = radical_count.get(rad, 0) + 1
    # 按字數排序（多 → 少），方便前端顯示
    return [
        {"radical": r, "count": c}
        for r, c in sorted(radical_count.items(), key=lambda x: -x[1])
    ]


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
