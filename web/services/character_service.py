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


def get_character_images(character: str, selected_calligraphers: Optional[List[str]] = None) -> Dict:
    """
    取得單一字元的所有書法家圖片 URL（不生成合併圖）

    Args:
        character: 中文字元
        selected_calligraphers: 選中的書法家顯示名稱（可選）

    Returns:
        dict: {character, images: [{calligrapher, image_url}], calligraphers_found, calligraphers_missing}
        或 {error: "錯誤訊息"}
    """
    from web.dependencies import get_character_index, get_name_font_label_dict
    char_index = get_character_index()
    char_map = char_index.get('character_map', {})

    if character not in char_map:
        return {"error": f"字元 '{character}' 不在索引中"}

    # font_label = "書法家·字帖"，例如 "顏真卿·多寶塔碑"
    label_map = get_name_font_label_dict()
    images = []
    available_cals = []

    fonts_root = PROJECT_ROOT / "Fonts" / "my_fonts"

    for cal_name, instances in char_map[character].items():
        font_label = label_map.get(cal_name, cal_name)
        display_name = font_label.split('·')[0] if '·' in font_label else font_label
        available_cals.append(font_label)

        # 若有指定書法家，以 display_name 比對（不含碑帖名稱）
        if selected_calligraphers and display_name not in selected_calligraphers:
            continue

        if not instances:
            continue

        # 取所有圖片（同一本字帖可能有多張同字，例如九成宮的「九」有兩個版本）
        for inst in instances:
            img_path = inst.get('image_path', '')
            if not img_path:
                continue
            try:
                from pathlib import Path as _Path
                rel = _Path(img_path).relative_to(fonts_root).as_posix()
            except (ValueError, TypeError):
                # 相對路徑 fallback
                rel = img_path.replace("\\", "/")
                if "Fonts/my_fonts/" in rel:
                    rel = rel.split("Fonts/my_fonts/")[1]

            images.append({
                "calligrapher": font_label,           # "顏真卿·多寶塔碑"
                "artist":    display_name,
                "book":      inst.get('book', font_label.split('·')[1] if '·' in font_label else ''),
                "font_id":   inst.get('font_id', ''),
                "image_url": f"/fonts/{rel}",
                "filename":  inst.get('filename', ''),
            })

    if not images:
        return {"error": f"字元 '{character}' 在選中的書法家中沒有找到"}

    # 計算找到與缺少的書法家（以 display_name 比對，去重）
    found = list(dict.fromkeys(img["calligrapher"] for img in images))
    if selected_calligraphers:
        avail_display_set = {
            fl.split('·')[0] if '·' in fl else fl
            for fl in available_cals
        }
        missing = [c for c in selected_calligraphers if c not in avail_display_set]
    else:
        missing = []

    return {
        "character": character,
        "images": images,
        "calligraphers_found": found,
        "calligraphers_missing": missing,
        "total_available": len(available_cals),
    }


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
    from web.dependencies import get_character_index, get_name_font_label_dict
    char_index = get_character_index()
    char_map = char_index.get('character_map', {})

    if character not in char_map:
        return {"error": f"字元 '{character}' 不在索引中，共有 {len(char_map)} 個可比對字元"}

    # 取得書法家·字帖標籤，並萃取 display_name（供 checkbox 過濾用）
    label_map = get_name_font_label_dict()
    seen_display = []
    available_display = []   # 去重後的 display_name 列表
    for k in char_map[character].keys():
        fl = label_map.get(k, k)
        d = fl.split('·')[0] if '·' in fl else fl
        if d not in seen_display:
            seen_display.append(d)
            available_display.append(d)

    # 計算找到與缺少的書法家（以 display_name 比對）
    if selected_calligraphers:
        avail_set = set(available_display)
        found = [c for c in selected_calligraphers if c in avail_set]
        missing = [c for c in selected_calligraphers if c not in avail_set]
    else:
        found = available_display
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
        "total_available": len(available_display),
    }
