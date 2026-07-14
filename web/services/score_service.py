"""
書法練字診斷服務

不做單一總分評分，改為分項量測 + 視覺化差異：
1. 整體形態相似度 — 重心對齊後的 Dice 係數 + Hu Moments 不變量比較
2. 結構平衡度 — 重心偏移、左右均衡、上下均衡
3. 差異疊合圖 — 逐像素標示多寫/少寫的筆劃

適合書法初學者，給予描述性回饋（非評分裁決）。
"""
import base64
import cv2
import numpy as np
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
FONTS_MY_FONTS = PROJECT_ROOT / "Fonts" / "my_fonts"


# ─── 影像前處理 ───────────────────────────────────────────────────────────────

def _remove_grid_lines(binary: np.ndarray) -> np.ndarray:
    """
    去除描紅/田字格練習紙上的格線干擾。

    練習紙格線常跟字的墨跡顏色相近（例如紅色格線配紅色字），轉灰階
    後 Otsu 二值化會把兩者都當成「墨跡」，導致自動裁切裁到整個格子
    外框而非只裁到字，比對時比例會完全跑掉。

    做法（形態學重建的簡化版）：
    1. 侵蝕原始墨跡遮罩 — 細格線（通常 1~3px）會被吃掉、消失或斷裂，
       粗筆劃（通常 10px 以上）大部分會留下較大的殘留區塊
    2. 侵蝕後保留「面積夠大」的連通元件當作「這是字」的種子——注意
       這裡刻意保留所有夠大的元件、不是只取最大的一個，因為很多中文
       字本來就有自然分開的部件（例如「三」的三橫、「州」的三點），
       只取最大元件會把其他真正的筆劃誤刪
    3. 回到「未侵蝕」的原始遮罩做連通元件分析，只保留跟種子有重疊的
       連通元件 — 這樣可以濾掉格線，同時保留字原本完整的筆劃粗細
       （不會因為侵蝕而變細）

    面積門檻用「相對最大元件的比例」而非絕對值，因為字被拍攝/縮放的
    尺寸不固定：格線交叉點、紙張污漬侵蝕後殘留通常遠小於任何一筆真正
    的筆劃（實測格線交叉點殘留 ~100px，真正筆劃殘留 ~350px 以上）。
    """
    ink = (binary < 128).astype(np.uint8) * 255
    if ink.sum() == 0:
        return binary

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    eroded = cv2.erode(ink, kernel, iterations=1)

    if eroded.sum() == 0:
        # 筆劃太細，侵蝕後什麼都不剩 —— 放棄濾格線，避免把字整個吃掉
        return binary

    num_e, labels_e, stats_e, _ = cv2.connectedComponentsWithStats(eroded, connectivity=8)
    areas = stats_e[1:, cv2.CC_STAT_AREA]
    area_threshold = max(40, 0.02 * areas.max())
    keep_labels = [i + 1 for i, a in enumerate(areas) if a >= area_threshold]
    seed = np.isin(labels_e, keep_labels)

    _, labels_o = cv2.connectedComponents(ink, connectivity=8)
    seed_labels = set(np.unique(labels_o[seed])) - {0}
    mask = np.isin(labels_o, list(seed_labels))

    result = np.where(mask, 0, 255).astype(np.uint8)  # 黑字(0)白底(255)
    return result


def _auto_crop_to_content(binary: np.ndarray, margin_ratio: float = 0.08) -> np.ndarray:
    """
    裁切到墨跡實際邊界框（留一點邊界），再置中補成正方形縮放到 256×256。

    解決手機拍照常見的留白/置中不一致問題：使用者拍照時字在畫面中的
    位置、周圍留白大小都不固定，若不裁切直接resize，字的相對大小會
    受原始留白比例影響，讓「重心對齊」「Dice係數」比較失真。
    """
    ink = binary < 128
    if not ink.any():
        return cv2.resize(binary, (256, 256), interpolation=cv2.INTER_AREA)

    ys, xs = np.where(ink)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())

    h, w = binary.shape
    bh, bw = y1 - y0 + 1, x1 - x0 + 1
    margin_y = int(bh * margin_ratio)
    margin_x = int(bw * margin_ratio)

    y0 = max(0, y0 - margin_y)
    y1 = min(h, y1 + margin_y + 1)
    x0 = max(0, x0 - margin_x)
    x1 = min(w, x1 + margin_x + 1)

    cropped = binary[y0:y1, x0:x1]

    # 補成正方形（置中），避免直接 resize 造成長寬比例失真
    ch, cw = cropped.shape
    side = max(ch, cw)
    square = np.full((side, side), 255, dtype=np.uint8)
    oy, ox = (side - ch) // 2, (side - cw) // 2
    square[oy:oy + ch, ox:ox + cw] = cropped

    return cv2.resize(square, (256, 256), interpolation=cv2.INTER_AREA)


def _skeletonize(binary: np.ndarray) -> np.ndarray:
    """
    骨架化：把筆劃縮成單像素寬的中心線（Zhang-Suen thinning）。

    消除毛筆/硬筆/手機拍照造成的筆劃粗細差異——評分時比的應該是
    「筆劃走向、結構」而不是「墨跡粗細」，骨架化後兩張圖的筆劃寬度
    都變成統一的 1px，Dice/Hu 比較才不會被筆的粗細影響。
    """
    ink_255 = (255 - binary).astype(np.uint8)  # thinning() 要求前景=255
    thin = cv2.ximgproc.thinning(ink_255, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    return 255 - thin  # 轉回黑字(0)白底(255)格式


def _binarize(img_gray: np.ndarray) -> np.ndarray:
    """灰階影像 → 256×256 二值化（黑字白底），去除格線干擾並自動裁切到內容邊界框"""
    # 偵測背景色（邊緣取樣）
    edge = np.concatenate([img_gray[0, :], img_gray[-1, :],
                           img_gray[:, 0], img_gray[:, -1]])
    if np.mean(edge) < 127:
        img_gray = 255 - img_gray  # 深色背景 → 反轉

    # 降噪 + Otsu 二值化
    img_gray = cv2.medianBlur(img_gray, 3)
    _, binary = cv2.threshold(img_gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = _remove_grid_lines(binary)
    return _auto_crop_to_content(binary)


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
    - Dice Coefficient（骨架化 + 重心對齊後的像素重疊率）× 60%
    - Hu Moments 相似度（旋轉/縮放不變量）× 40%

    骨架化（見 _skeletonize）讓比較聚焦在筆劃走向與結構本身，
    不受毛筆/硬筆/拍照造成的筆劃粗細差異影響。
    """
    # === Dice（骨架化 + 重心對齊後）===
    u_thin = _skeletonize(user_bin)
    r_thin = _skeletonize(ref_bin)

    u_aligned = _align_centroid(u_thin)
    r_aligned = _align_centroid(r_thin)

    u_ink = (u_aligned < 128).astype(np.uint8) * 255
    r_ink = (r_aligned < 128).astype(np.uint8) * 255

    # 骨架是 1px 寬的線，直接比對重疊會對「差一兩個像素」極度敏感
    # （筆順稍有偏移就整條線完全不重疊），膨脹幾個像素給一點容許誤差，
    # 兩邊用同樣的膨脹幅度，維持公平比較。
    kernel = np.ones((3, 3), np.uint8)
    u_ink = cv2.dilate(u_ink, kernel, iterations=6).astype(np.float32) / 255
    r_ink = cv2.dilate(r_ink, kernel, iterations=6).astype(np.float32) / 255

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
    """
    根據個別量測值生成描述性文字回饋。

    刻意不合成單一總分：形態相似度跟結構平衡度是兩個不同維度的量測，
    用什麼權重合成「總評」沒有明確依據，容易誤導成「這是你寫得好不好
    的裁判分數」。改成各自獨立給描述性回饋，讓使用者看量測值本身判斷。
    """
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
        "shape":   shape_fb,
        "balance": balance_fb,
    }


# ─── 差異疊合圖 ────────────────────────────────────────────────────────────────

def _aligned_ink_masks(user_bin: np.ndarray, ref_bin: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """重心對齊後，回傳雙方的墨跡遮罩（uint8，255=有墨、0=無墨）"""
    u_aligned = _align_centroid(user_bin)
    r_aligned = _align_centroid(ref_bin)
    u_ink = (u_aligned < 128).astype(np.uint8) * 255
    r_ink = (r_aligned < 128).astype(np.uint8) * 255
    return u_ink, r_ink


def _encode_mask_png(mask_255: np.ndarray) -> str:
    """把 0/255 遮罩編碼成 base64 PNG data URL，失敗時回傳空字串"""
    success, buf = cv2.imencode('.png', mask_255)
    if not success:
        return ""
    b64 = base64.b64encode(buf.tobytes()).decode('ascii')
    return f"data:image/png;base64,{b64}"


def _generate_diff_overlay(u_ink: np.ndarray, r_ink: np.ndarray) -> str:
    """
    生成使用者與大師的差異疊合圖（base64 PNG data URL）。

    輸入為已經重心對齊過的墨跡遮罩（見 `_aligned_ink_masks`）：
    - 深灰 [70, 70, 70]  ：雙方都有墨（相符筆劃）
    - 紅色 [220, 60, 60] ：使用者多寫（user 有墨，master 無墨）
    - 藍色 [60, 110, 220]：使用者少寫（master 有墨，user 無墨）
    - 淺灰 [240, 240, 240]：雙方皆無墨（空白區域）

    Returns: "data:image/png;base64,..." 字串，失敗時回傳 ""
    """
    u_mask = u_ink > 0
    r_mask = r_ink > 0

    h, w = u_ink.shape
    overlay = np.full((h, w, 3), 240, dtype=np.uint8)   # 淺灰背景

    overlay[u_mask & r_mask]  = [70, 70, 70]    # 雙方都有墨 → 深灰（相符）
    overlay[u_mask & ~r_mask] = [220, 60, 60]   # 使用者多寫 → 紅
    overlay[~u_mask & r_mask] = [60, 110, 220]  # 使用者少寫 → 藍

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
    主要診斷函式（單一書法家）。

    Parameters:
        user_img_bytes: 使用者上傳的圖片 bytes
        char:           所練的中文字
        cal_name:       指定書法家顯示名稱（None = 自動選第一位）

    Returns:
        {
            char, shape_score, balance_score,
            balance_detail, feedback, ref_cal_name, ref_image_url
        }

    不回傳單一「總分」——形態相似度與結構平衡度是兩個獨立量測維度，
    合成一個總分需要武斷的權重假設，沒有依據。改為分項呈現量測值，
    讓使用者自己判讀，搭配差異疊圖看實際差在哪裡。
    """
    user_bin = load_user_image(user_img_bytes)
    ref_bin, ref_display, ref_url = _load_reference_binary(char, cal_name)
    return _build_result(user_bin, ref_bin, char, ref_display, ref_url)


def _build_result(user_bin: np.ndarray, ref_bin: np.ndarray, char: str,
                   ref_display: str, ref_url: str) -> dict:
    """組出單一書法家的診斷結果（供 analyze_character / analyze_character_all 共用）"""
    shape   = _compute_shape_similarity(user_bin, ref_bin)
    balance = _compute_balance(user_bin)
    fb      = _make_feedback(shape, balance["score"])

    u_ink, r_ink = _aligned_ink_masks(user_bin, ref_bin)
    diff_img = _generate_diff_overlay(u_ink, r_ink)

    return {
        "char":          char,
        "shape_score":   round(shape, 3),
        "balance_score": round(balance["score"], 3),
        "balance_detail": {
            "lr_ratio":    round(balance["lr_ratio"], 3),
            "tb_ratio":    round(balance["tb_ratio"], 3),
            "centroid_x":  round(balance["centroid_x"], 3),
            "centroid_y":  round(balance["centroid_y"], 3),
        },
        "feedback": {
            "shape":   fb["shape"],
            "balance": fb["balance"],
        },
        "ref_cal_name":  ref_display,
        "ref_image_url": ref_url,
        "diff_image":    diff_img,
        # 重心對齊後的墨跡遮罩（0/255），供前端「差異敏感度」滑桿即時重繪疊圖用，
        # 不用每次調整滑桿都重打一次 API。
        "user_mask_image": _encode_mask_png(u_ink),
        "ref_mask_image":  _encode_mask_png(r_ink),
    }


def analyze_character_all(user_img_bytes: bytes, char: str) -> dict:
    """
    一次分析：對某字所有有寫過的書法家分別比對，依形態相似度由高到低排序。

    解決「每次只能挑一位書法家、換人要重新上傳」的痛點——
    使用者上傳一次圖片，就能看到自己的字跟全部書法家的比較結果。

    Returns:
        {"char": char, "results": [同 analyze_character 的單筆結果, ...]}
    """
    from web.dependencies import get_character_index, get_name_font_label_dict
    char_index = get_character_index()
    char_map = char_index.get("character_map", {})

    if char not in char_map:
        raise ValueError(f"字庫中找不到「{char}」，目前不支援此字")

    user_bin = load_user_image(user_img_bytes)
    name_map = get_name_font_label_dict()

    results = []
    for cal_name, instances in char_map[char].items():
        display = name_map.get(cal_name, cal_name)
        img_path = None
        for inst in instances:
            img_path_str = inst.get("image_path", "")
            if not img_path_str:
                continue
            candidate = _resolve_image_path(img_path_str)
            if candidate.exists():
                img_path = candidate
                break
        if img_path is None:
            continue

        ref_gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if ref_gray is None:
            continue

        ref_bin = _binarize(ref_gray)
        results.append(_build_result(user_bin, ref_bin, char, display, _image_url_from_path(img_path)))

    if not results:
        raise ValueError(f"找不到「{char}」的有效參考圖片")

    results.sort(key=lambda r: r["shape_score"], reverse=True)
    return {"char": char, "results": results}
