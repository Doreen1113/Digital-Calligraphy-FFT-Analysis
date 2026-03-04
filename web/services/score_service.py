"""
書法練字評分服務

評分維度：
1. 整體形態相似度 — 重心對齊後的 Dice 係數 + Hu Moments 不變量比較
2. 結構平衡度 — 重心偏移、左右均衡、上下均衡

適合書法初學者，給予鼓勵性回饋。
"""
import base64
import cv2
import numpy as np
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
FONTS_MY_FONTS = PROJECT_ROOT / "Fonts" / "my_fonts"


# ─── 影像前處理 ───────────────────────────────────────────────────────────────

def _binarize(img_gray: np.ndarray) -> np.ndarray:
    """灰階影像 → 256×256 二值化（黑字白底）"""
    # 偵測背景色（邊緣取樣）
    edge = np.concatenate([img_gray[0, :], img_gray[-1, :],
                           img_gray[:, 0], img_gray[:, -1]])
    if np.mean(edge) < 127:
        img_gray = 255 - img_gray  # 深色背景 → 反轉

    # 降噪 + Otsu 二值化
    img_gray = cv2.medianBlur(img_gray, 3)
    _, binary = cv2.threshold(img_gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.resize(binary, (256, 256), interpolation=cv2.INTER_AREA)


def load_user_image(img_bytes: bytes) -> np.ndarray:
    """載入使用者上傳的圖片 bytes → 256×256 二值化影像"""
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("無法解析圖片，請確認格式正確（支援 JPG/PNG/WebP/BMP）")
    return _binarize(img)


def _resolve_image_path(img_path_str: str) -> Path:
    """解析 character_index 中儲存的圖片路徑（支援絕對/相對路徑）

    字元索引存的可能是 Windows 絕對路徑（C:/My_Project/...），
    在 Linux/Docker 上這些路徑不存在，需要自動轉換成相對路徑。
    """
    norm = img_path_str.replace("\\", "/")
    p = Path(norm)

    # 若路徑本身就可用，直接回傳
    if p.exists():
        return p

    # Windows 絕對路徑在 Linux 失效 → 擷取 Fonts/my_fonts/ 之後的相對部分
    for marker in ("Fonts/my_fonts/", "data/fonts/"):
        if marker in norm:
            rel = norm.split(marker, 1)[-1]
            candidate = FONTS_MY_FONTS / rel if marker == "Fonts/my_fonts/" else PROJECT_ROOT / "data" / "fonts" / rel
            if candidate.exists():
                return candidate

    # 相對路徑：相對於專案根目錄
    if not p.is_absolute():
        return PROJECT_ROOT / norm.lstrip("./")

    return p  # 回傳原路徑（exists() 將回傳 False）


def _image_url_from_path(img_path: Path) -> str:
    """從絕對路徑產生 /fonts/... URL"""
    try:
        rel = img_path.relative_to(FONTS_MY_FONTS)
        return f"/fonts/{rel.as_posix()}"
    except ValueError:
        path_str = str(img_path).replace("\\", "/")
        if "Fonts/my_fonts/" in path_str:
            return "/fonts/" + path_str.split("Fonts/my_fonts/")[-1]
        return ""


# ─── 取得書法家資料 ───────────────────────────────────────────────────────────

def get_available_calligraphers(char: str) -> list[dict]:
    """
    取得某字可用的書法家清單（各帶一張圖片 URL）

    Returns: [{"name": "顏真卿・玄秘塔碑", "image_url": "/fonts/..."}, ...]
    使用 font_label（書法家・字帖）以區分同一書法家的不同版本。
    """
    from web.dependencies import get_character_index, get_name_font_label_dict
    char_index = get_character_index()
    char_map = char_index.get("character_map", {})

    if char not in char_map:
        return []

    name_map = get_name_font_label_dict()
    result = []

    for cal_name, instances in char_map[char].items():
        if not instances:
            continue
        img_path_str = instances[0].get("image_path", "")
        if not img_path_str:
            continue
        img_path = _resolve_image_path(img_path_str)
        if not img_path.exists():
            continue
        label = name_map.get(cal_name, cal_name)
        result.append({
            "name": label,
            "image_url": _image_url_from_path(img_path),
        })

    return result


def _load_reference_binary(char: str,
                            cal_display_name: Optional[str] = None
                            ) -> tuple[np.ndarray, str, str]:
    """
    從字元索引載入參考書法家的二值化圖片。

    Returns:
        (binary_256x256, display_name, image_url)
    """
    from web.dependencies import get_character_index, get_name_font_label_dict
    char_index = get_character_index()
    char_map = char_index.get("character_map", {})

    if char not in char_map:
        raise ValueError(f"字庫中找不到「{char}」，目前不支援此字")

    name_map = get_name_font_label_dict()
    cal_data = char_map[char]

    # 找指定書法家（font_label 比對），或回退至第一個有效圖片
    selected_instances = None
    selected_display = None

    for cal_name, instances in cal_data.items():
        display = name_map.get(cal_name, cal_name)
        if cal_display_name and display != cal_display_name:
            continue
        for inst in instances:
            img_path_str = inst.get("image_path", "")
            if not img_path_str:
                continue
            img_path = _resolve_image_path(img_path_str)
            if img_path.exists():
                selected_instances = (img_path, display)
                break
        if selected_instances:
            break

    if selected_instances is None:
        raise ValueError(f"找不到「{char}」的有效參考圖片")

    img_path, display_name = selected_instances
    ref_gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if ref_gray is None:
        raise ValueError("無法載入參考圖片")

    ref_bin = _binarize(ref_gray)
    return ref_bin, display_name, _image_url_from_path(img_path)


# ─── 評分演算法 ────────────────────────────────────────────────────────────────

def _align_centroid(binary: np.ndarray) -> np.ndarray:
    """
    將字的重心平移到圖像中心，用於比較前的對齊。
    binary: 256×256，黑字(0)白底(255)
    """
    ink = (binary < 128).astype(np.float32)
    total = np.sum(ink)
    if total < 20:
        return binary

    ys, xs = np.where(ink > 0)
    cx, cy = np.mean(xs), np.mean(ys)
    h, w = binary.shape
    dx, dy = int(w / 2 - cx), int(h / 2 - cy)

    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(binary, M, (w, h), borderValue=255)


def _compute_shape_similarity(user_bin: np.ndarray,
                               ref_bin: np.ndarray) -> float:
    """
    整體形態相似度 (0.0 ~ 1.0)

    方法：
    - Dice Coefficient（重心對齊後的像素重疊率）× 60%
    - Hu Moments 相似度（旋轉/縮放不變量）× 40%
    """
    # === Dice（重心對齊後）===
    u_aligned = _align_centroid(user_bin)
    r_aligned = _align_centroid(ref_bin)

    u_ink = (u_aligned < 128).astype(np.float32)
    r_ink = (r_aligned < 128).astype(np.float32)

    intersection = np.sum(u_ink * r_ink)
    denom = np.sum(u_ink) + np.sum(r_ink)
    dice = 2 * intersection / (denom + 1e-6)

    # === Hu Moments ===
    u_cv = (255 - user_bin).astype(np.uint8)   # ink=255
    r_cv = (255 - ref_bin).astype(np.uint8)

    mu = cv2.moments(u_cv)
    mr = cv2.moments(r_cv)

    hu_u = cv2.HuMoments(mu).flatten()
    hu_r = cv2.HuMoments(mr).flatten()

    # Log transform（Hu Moments 數值範圍極寬）
    eps = 1e-10
    hu_u = -np.sign(hu_u) * np.log10(np.abs(hu_u) + eps)
    hu_r = -np.sign(hu_r) * np.log10(np.abs(hu_r) + eps)

    hu_sim = 1.0 / (1.0 + np.mean(np.abs(hu_u - hu_r)))

    similarity = 0.6 * dice + 0.4 * hu_sim
    return float(np.clip(similarity, 0.0, 1.0))


def _compute_balance(binary: np.ndarray) -> dict:
    """
    結構平衡度分析

    評估：
    - 重心偏移（距幾何中心的偏差）× 40%
    - 左右均衡度 × 30%
    - 上下均衡度 × 30%

    Returns dict with score(0-1) and details.
    """
    ink = (binary < 128).astype(np.float32)
    total_ink = float(np.sum(ink))

    if total_ink < 50:
        return {
            "score": 0.0,
            "lr_ratio": 0.0,
            "tb_ratio": 0.0,
            "centroid_x": 0.5,
            "centroid_y": 0.5,
        }

    h, w = ink.shape
    ys, xs = np.where(ink > 0)
    cx = float(np.mean(xs)) / w   # 0~1
    cy = float(np.mean(ys)) / h   # 0~1

    # 重心偏移分數（越靠近 0.5 越好）
    cx_dev = abs(cx - 0.5)
    cy_dev = abs(cy - 0.5)
    center_score = max(0.0, 1.0 - (cx_dev + cy_dev) * 2.5)

    # 左右均衡
    left  = float(np.sum(ink[:, :w // 2]))
    right = float(np.sum(ink[:, w // 2:]))
    lr_ratio = min(left, right) / (max(left, right) + 1e-6)

    # 上下均衡
    top = float(np.sum(ink[:h // 2, :]))
    bot = float(np.sum(ink[h // 2:, :]))
    tb_ratio = min(top, bot) / (max(top, bot) + 1e-6)

    score = center_score * 0.4 + lr_ratio * 0.3 + tb_ratio * 0.3

    return {
        "score": float(np.clip(score, 0.0, 1.0)),
        "lr_ratio": float(lr_ratio),
        "tb_ratio": float(tb_ratio),
        "centroid_x": float(cx),
        "centroid_y": float(cy),
    }


def _make_feedback(shape: float, balance: float) -> dict:
    """根據分數生成鼓勵性文字回饋"""
    total = shape * 0.7 + balance * 0.3

    if total >= 0.72:
        overall = "非常出色！形態與結構均達高水準，已有書法家的神韻。"
    elif total >= 0.58:
        overall = "寫得不錯！基本功具備，繼續臨摹會更精進。"
    elif total >= 0.42:
        overall = "有進步空間，多觀察大師的筆劃走向，持續練習。"
    else:
        overall = "初學者加油！每天堅持練習，一定會有進步的。"

    if shape >= 0.65:
        shape_fb = "筆劃走向與大師高度吻合，形態掌握良好"
    elif shape >= 0.48:
        shape_fb = "整體輪廓接近，可再留意細節筆劃的起收筆"
    else:
        shape_fb = "建議多臨摹大師筆劃的走向、輕重與轉折"

    if balance >= 0.68:
        balance_fb = "結構均衡，字形端正，重心穩定"
    elif balance >= 0.50:
        balance_fb = "結構尚可，留意各部件的比例與重心"
    else:
        balance_fb = "字的重心偏移，注意讓筆劃分佈更均衡"

    return {
        "overall": overall,
        "shape":   shape_fb,
        "balance": balance_fb,
        "total":   float(total),
    }


# ─── 差異疊合圖 ────────────────────────────────────────────────────────────────

def _generate_diff_overlay(user_bin: np.ndarray, ref_bin: np.ndarray) -> str:
    """
    生成使用者與大師的差異疊合圖（base64 PNG data URL）。

    重心對齊後逐像素比對：
    - 深灰 [70, 70, 70]  ：雙方都有墨（相符筆劃）
    - 紅色 [220, 60, 60] ：使用者多寫（user 有墨，master 無墨）
    - 藍色 [60, 110, 220]：使用者少寫（master 有墨，user 無墨）
    - 淺灰 [240, 240, 240]：雙方皆無墨（空白區域）

    Returns: "data:image/png;base64,..." 字串，失敗時回傳 ""
    """
    u_aligned = _align_centroid(user_bin)
    r_aligned = _align_centroid(ref_bin)

    # ink mask: True = 有墨（pixel < 128）
    u_ink = u_aligned < 128
    r_ink = r_aligned < 128

    h, w = u_aligned.shape
    overlay = np.full((h, w, 3), 240, dtype=np.uint8)   # 淺灰背景

    # 雙方都有墨 → 深灰（相符）
    overlay[u_ink & r_ink] = [70, 70, 70]

    # 使用者多寫 → 紅
    overlay[u_ink & ~r_ink] = [220, 60, 60]

    # 使用者少寫 → 藍
    overlay[~u_ink & r_ink] = [60, 110, 220]

    success, buf = cv2.imencode('.png', overlay)
    if not success:
        return ""
    b64 = base64.b64encode(buf.tobytes()).decode('ascii')
    return f"data:image/png;base64,{b64}"


# ─── 主要評分入口 ─────────────────────────────────────────────────────────────

def analyze_character(user_img_bytes: bytes,
                      char: str,
                      cal_name: Optional[str] = None) -> dict:
    """
    主要評分函式。

    Parameters:
        user_img_bytes: 使用者上傳的圖片 bytes
        char:           所練的中文字
        cal_name:       指定書法家顯示名稱（None = 自動選第一位）

    Returns:
        {
            char, total_score, shape_score, balance_score,
            balance_detail, feedback, ref_cal_name, ref_image_url
        }
    """
    user_bin = load_user_image(user_img_bytes)
    ref_bin, ref_display, ref_url = _load_reference_binary(char, cal_name)

    shape   = _compute_shape_similarity(user_bin, ref_bin)
    balance = _compute_balance(user_bin)
    fb      = _make_feedback(shape, balance["score"])
    diff_img = _generate_diff_overlay(user_bin, ref_bin)

    return {
        "char":          char,
        "total_score":   round(fb["total"], 3),
        "shape_score":   round(shape, 3),
        "balance_score": round(balance["score"], 3),
        "balance_detail": {
            "lr_ratio":    round(balance["lr_ratio"], 3),
            "tb_ratio":    round(balance["tb_ratio"], 3),
            "centroid_x":  round(balance["centroid_x"], 3),
            "centroid_y":  round(balance["centroid_y"], 3),
        },
        "feedback": {
            "overall": fb["overall"],
            "shape":   fb["shape"],
            "balance": fb["balance"],
        },
        "ref_cal_name":  ref_display,
        "ref_image_url": ref_url,
        "diff_image":    diff_img,
    }
