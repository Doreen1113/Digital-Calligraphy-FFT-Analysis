"""
上傳比對 API

使用者上傳手寫字圖片，與書法大師的版本並排比對。
支援 JPG / PNG / WebP / BMP 格式，最大 5 MB。
"""
import asyncio
import io
import threading
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

router = APIRouter()

_OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "upload"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_MAX_CACHED_FILES = 100   # 最多保留幾張比對圖

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
_MAX_SIZE = 5 * 1024 * 1024   # 5 MB
_plot_lock = threading.Lock()


def _preprocess_upload(raw: bytes) -> np.ndarray:
    """將上傳圖片轉為乾淨的二值化影像（黑字白底）"""
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("無法解析圖片，請確認格式正確")

    # 亮度增強
    img = cv2.multiply(img, np.array([1.25]))
    img = np.clip(img, 0, 255).astype(np.uint8)

    # 自動偵測背景色，確保黑字白底
    edge = np.concatenate([img[0, :], img[-1, :], img[:, 0], img[:, -1]])
    if np.mean(edge) < 127:            # 深色背景 → 反轉
        img = 255 - img

    # 降噪 + 二值化
    img = cv2.medianBlur(img, 3)
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 調整大小到統一尺寸
    binary = cv2.resize(binary, (256, 256), interpolation=cv2.INTER_AREA)
    return binary


def _generate_comparison(char: str, user_img: np.ndarray,
                          calligraphers: Optional[List[str]]) -> str:
    """生成使用者 + 書法家的並排比對圖，回傳輸出路徑"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    from web.dependencies import get_character_index, get_name_display_dict
    char_index = get_character_index()
    char_map   = char_index.get('character_map', {})
    name_map   = get_name_display_dict()

    if char not in char_map:
        raise ValueError(f"字庫中沒有「{char}」，無法比對")

    # 取得各書法家圖片
    cal_images = []
    for cal_name, instances in char_map[char].items():
        display = name_map.get(cal_name, cal_name)
        if calligraphers and display not in calligraphers:
            continue
        if not instances:
            continue
        img_path = instances[0].get('image_path', '')
        img_path = img_path.replace("\\", "/")
        if not img_path.startswith('./'):
            img_path = './' + img_path
        full_path = Path(__file__).parent.parent.parent / img_path.lstrip('./')
        cal_img = cv2.imread(str(full_path), cv2.IMREAD_GRAYSCALE)
        if cal_img is not None:
            cal_images.append((display, cal_img))

    if not cal_images:
        raise ValueError(f"找不到「{char}」的書法家圖片")

    n_cols = len(cal_images) + 1    # +1 for user
    fig_w  = max(n_cols * 2.2, 6)

    with _plot_lock:
        fig, axes = plt.subplots(1, n_cols, figsize=(fig_w, 2.8))
        if n_cols == 1:
            axes = [axes]

        # --- 使用者的字 ---
        axes[0].imshow(user_img, cmap='gray', vmin=0, vmax=255)
        axes[0].set_title('你的字', fontsize=10, fontproperties=_get_font_prop(),
                          color='#C62828', fontweight='bold')
        axes[0].axis('off')

        # --- 書法家 ---
        for i, (name, img) in enumerate(cal_images, start=1):
            axes[i].imshow(img, cmap='gray', vmin=0, vmax=255)
            axes[i].set_title(name, fontsize=10, fontproperties=_get_font_prop())
            axes[i].axis('off')

        plt.tight_layout(pad=0.5)

        # 存檔
        import hashlib, time
        h = hashlib.md5(f"{char}{time.time()}".encode()).hexdigest()[:8]
        out_file = _OUTPUT_DIR / f"upload_{char}_{h}.png"
        plt.savefig(str(out_file), dpi=120, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)

    # 超過上限時，刪除最舊的檔案
    files = sorted(_OUTPUT_DIR.glob("upload_*.png"), key=lambda f: f.stat().st_mtime)
    for old in files[:-_MAX_CACHED_FILES]:
        old.unlink(missing_ok=True)

    return str(out_file)


def _get_font_prop():
    """取得中文字型屬性"""
    import matplotlib.font_manager as fm
    for name in ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Noto Sans CJK TC']:
        try:
            return fm.FontProperties(family=name)
        except Exception:
            pass
    return fm.FontProperties()


@router.post("/compare")
async def upload_compare(
    file: UploadFile = File(..., description="手寫字圖片（JPG/PNG/WebP/BMP，≤ 5 MB）"),
    char: str = Form(..., min_length=1, max_length=1, description="所寫的中文字"),
    calligraphers: Optional[str] = Form(None, description="書法家名稱，逗號分隔，留空=全部"),
):
    """上傳手寫字圖片，與書法大師並排比對"""
    # 驗證格式
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(400, detail=f"不支援的圖片格式：{file.content_type}。請上傳 JPG/PNG/WebP/BMP")

    raw = await file.read()
    if len(raw) > _MAX_SIZE:
        raise HTTPException(400, detail=f"圖片超過 5 MB（目前 {len(raw) // 1024} KB）")

    # 解析書法家列表
    cal_list = [c.strip() for c in calligraphers.split(',')] if calligraphers else None

    try:
        user_img  = _preprocess_upload(raw)
        out_path  = await asyncio.to_thread(
            _generate_comparison, char, user_img, cal_list
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"生成比對圖時發生錯誤：{str(e)}")

    # 回傳圖片 URL（相對於 /output）
    rel = Path(out_path).relative_to(
        Path(__file__).parent.parent.parent / "output"
    )
    return {
        "image_url": f"/output/{rel.as_posix()}",
        "character": char,
    }
