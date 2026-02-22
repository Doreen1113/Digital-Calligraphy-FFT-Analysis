"""
圖片快取服務

管理比對圖片的快取路徑與生命週期
"""
import os
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_comparison_cache_path(character: str, calligraphers: list = None) -> str:
    """
    生成比對圖片的快取路徑

    Args:
        character: 字元
        calligraphers: 書法家列表（可選）

    Returns:
        快取檔案的完整路徑
    """
    cache_dir = PROJECT_ROOT / "output" / "comparison"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if calligraphers:
        # 有篩選時加上 hash 避免衝突
        cal_key = "_".join(sorted(calligraphers))
        hash_suffix = hashlib.md5(cal_key.encode('utf-8')).hexdigest()[:8]
        filename = f"web_{character}_{hash_suffix}.png"
    else:
        filename = f"web_{character}_all.png"

    return str(cache_dir / filename)


def is_cached(cache_path: str) -> bool:
    """檢查快取是否存在"""
    return os.path.exists(cache_path)


def get_cache_url(cache_path: str) -> str:
    """
    將快取檔案路徑轉為 URL

    例如: C:/project/output/comparison/web_天_all.png
       -> /output/comparison/web_天_all.png
    """
    output_root = str(PROJECT_ROOT / "output")
    rel = os.path.relpath(cache_path, output_root)
    return f"/output/{rel.replace(os.sep, '/')}"


def image_path_to_url(image_path: str) -> str:
    """
    將書法圖片的檔案路徑轉為 URL

    例如: ./Fonts/my_fonts/00/char_0001.png -> /fonts/00/char_0001.png
    """
    p = image_path.replace("\\", "/")
    p = p.replace("./Fonts/my_fonts/", "")
    return f"/fonts/{p}"
