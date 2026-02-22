"""
字元比對服務

封裝 character_comparator.compare_character() 並加入快取與線程安全機制
"""
import os
import sys
import threading
from typing import List, Optional, Dict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.services.cache_service import get_comparison_cache_path, is_cached, get_cache_url

# matplotlib 不是線程安全的，需要鎖
_matplotlib_lock = threading.Lock()


def compare_single(character: str, selected_calligraphers: Optional[List[str]] = None) -> Dict:
    """
    比對單一字元，回傳圖片 URL 和元資料

    Args:
        character: 中文字元
        selected_calligraphers: 選中的書法家顯示名稱（可選）

    Returns:
        dict: {character, image_url, calligraphers_found, calligraphers_missing}
        或 {error: "錯誤訊息"}
    """
    # 檢查字元是否在索引中
    from web.dependencies import get_character_index, get_name_display_dict
    char_index = get_character_index()
    char_map = char_index.get('character_map', {})

    if character not in char_map:
        return {"error": f"字元 '{character}' 不在索引中，共有 {len(char_map)} 個可比對字元"}

    # 取得書法家資訊
    name_map = get_name_display_dict()
    available_cals = [name_map.get(k, k) for k in char_map[character].keys()]

    # 計算找到與缺少的書法家
    if selected_calligraphers:
        found = [c for c in selected_calligraphers if c in available_cals]
        missing = [c for c in selected_calligraphers if c not in available_cals]
    else:
        found = available_cals
        missing = []

    if not found:
        return {"error": f"字元 '{character}' 在選中的書法家中沒有找到"}

    # 檢查快取
    cache_path = get_comparison_cache_path(character, selected_calligraphers)

    if not is_cached(cache_path):
        # 需要生成圖片
        try:
            # 確保目錄存在
            cache_dir = os.path.dirname(cache_path)
            os.makedirs(cache_dir, exist_ok=True)

            with _matplotlib_lock:
                from character_comparator import compare_character
                # 再次檢查以避免並行重複生成
                if not os.path.exists(cache_path):
                    compare_character(
                        character,
                        output_path=cache_path,
                        selected_calligraphers=selected_calligraphers
                    )
        except Exception as e:
            import traceback
            error_msg = str(e)
            # 提供更詳細的錯誤資訊用於除錯
            print(f"[Error] 生成 '{character}' 比對圖失敗:")
            print(f"  Cache path: {cache_path}")
            print(f"  Selected calligraphers: {selected_calligraphers}")
            print(f"  Error: {error_msg}")
            traceback.print_exc()
            return {"error": f"生成比對圖片失敗: {error_msg}"}

    # 確認圖片已生成
    if not os.path.exists(cache_path):
        return {"error": f"無法產生字元 '{character}' 的比對圖"}

    return {
        "character": character,
        "image_url": get_cache_url(cache_path),
        "calligraphers_found": found,
        "calligraphers_missing": missing,
        "total_available": len(available_cals),
    }
