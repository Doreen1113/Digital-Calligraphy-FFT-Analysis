"""
共用依賴模組

提供全域共用的配置、索引載入、資料載入器等
使用 @lru_cache 確保只載入一次
"""
import json
import os
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


@lru_cache()
def get_project_root() -> str:
    """取得專案根目錄路徑"""
    return str(PROJECT_ROOT)


def _get_config():
    """取得配置實例（內部用）"""
    from src.utils import get_config
    return get_config()


@lru_cache()
def get_character_index() -> dict:
    """載入同字索引到記憶體（只載入一次）"""
    config = _get_config()
    index_path = config.get_index_path('character_index')

    if not os.path.exists(index_path):
        return {}

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache()
def get_fonts_index() -> dict:
    """載入字庫索引到記憶體（只載入一次）"""
    config = _get_config()
    index_path = config.get_index_path('fonts_index')

    if not os.path.exists(index_path):
        return {}

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache()
def get_calligrapher_list() -> list:
    """取得書法家配置列表"""
    config = _get_config()
    return config.get_calligraphers()


@lru_cache()
def get_name_to_display() -> tuple:
    """取得英文名到中文顯示名的對應（回傳 tuple 以支援 lru_cache）"""
    cals = get_calligrapher_list()
    # lru_cache 需要 hashable，所以回傳 tuple of tuples
    return tuple((cal['name'], cal['display_name']) for cal in cals)


def get_name_display_dict() -> dict:
    """取得英文名到中文顯示名的字典"""
    return dict(get_name_to_display())


@lru_cache()
def get_name_to_font_label() -> tuple:
    """取得英文名到「書法家·字帖」標籤的對應

    例如：
      "yan_zhenqing"    → "顏真卿·玄秘塔碑"
      "yan_zhenqing_07" → "顏真卿·多寶塔碑"
      "zhiyong"         → "智永·真草千字文"
    """
    cals = get_calligrapher_list()
    result = []
    for cal in cals:
        book = cal.get('book', '')
        label = f"{cal['display_name']}·{book}" if book else cal['display_name']
        result.append((cal['name'], label))
    return tuple(result)


def get_name_font_label_dict() -> dict:
    """取得英文名到 font_label 的字典（用於顯示書法家+字帖）"""
    return dict(get_name_to_font_label())


def get_font_label_to_name_dict() -> dict:
    """取得 font_label 到英文名的反向字典（用於篩選）"""
    return {label: name for name, label in get_name_to_font_label()}


def validate_environment():
    """驗證執行環境，啟動時呼叫"""
    config = _get_config()

    # 檢查索引檔案
    char_index_path = config.get_index_path('character_index')
    fonts_index_path = config.get_index_path('fonts_index')

    if not os.path.exists(char_index_path):
        print(f"[Warning] 同字索引不存在: {char_index_path}")
        print("         請先執行: python main.py -> 選項 1（建立索引）")
    else:
        char_index = get_character_index()
        char_count = len(char_index.get('character_map', {}))
        common_count = len(char_index.get('common_characters', []))
        print(f"[OK] 同字索引已載入: {char_count} 個字元, {common_count} 個共有字")

    if not os.path.exists(fonts_index_path):
        print(f"[Warning] 字庫索引不存在: {fonts_index_path}")
    else:
        fonts_index = get_fonts_index()
        cal_count = len(fonts_index.get('calligraphers', {}))
        print(f"[OK] 字庫索引已載入: {cal_count} 位書法家")

    # 檢查書法圖片目錄
    fonts_dir = PROJECT_ROOT / "Fonts" / "my_fonts"
    if fonts_dir.exists():
        subdirs = [d for d in fonts_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        print(f"[OK] 書法圖片目錄: {len(subdirs)} 個子目錄")
    else:
        print(f"[Warning] 書法圖片目錄不存在: {fonts_dir}")

    # 檢查輸出目錄
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "comparison").mkdir(exist_ok=True)
    (output_dir / "batch").mkdir(exist_ok=True)
    print(f"[OK] 輸出目錄已就緒")

    print()
    print("Web 伺服器就緒！")
