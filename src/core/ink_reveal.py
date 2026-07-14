"""
真跡墨塊拆解與漸進浮現動畫產生器

把一張書法家真跡圖片，依連通元件拆成獨立的墨跡區塊，依「由上到下、
由左到右」的閱讀順序排序，輸出成一個帶有 CSS 動畫 class 的 SVG 字串，
讓前端可以播放「這個字正在被寫出來」的漸進浮現效果。

注意：這不是真正的筆順辨識。連在一起的筆畫（尤其行書/草書的牽絲連筆）
會被當成同一塊一起出現，順序也只是位置上的閱讀順序，不保證是書寫時的
實際筆順。見 docs 討論：真正的逐筆筆順需要人工標註或更複雜的筆畫分割
演算法，這裡採用的是可行的折衷方案。
"""
import cv2
import numpy as np


def generate_ink_reveal_svg(image_path: str, min_area: int = 15, row_tolerance_ratio: float = 0.15) -> dict:
    """
    讀取一張書法字圖片，拆解成獨立墨跡區塊並排序，回傳 SVG 內容。

    Returns:
        {"svg": "<svg ...>...</svg>", "piece_count": int, "width": int, "height": int}
        若讀取失敗回傳 None。
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    h, w = binary.shape

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    blobs = []
    for i in range(1, num_labels):  # 0 是背景
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        cy, cx = centroids[i][1], centroids[i][0]
        mask = np.where(labels == i, 255, 0).astype(np.uint8)
        blobs.append({"mask": mask, "cy": cy, "cx": cx})

    if not blobs:
        return {"svg": f'<svg viewBox="0 0 {w} {h}"></svg>', "piece_count": 0, "width": w, "height": h}

    # 閱讀順序排序：先用 y 座標粗略分行，再同一行內由左到右
    blobs.sort(key=lambda b: b["cy"])
    row_tol = h * row_tolerance_ratio
    rows = []
    for b in blobs:
        placed = False
        for row in rows:
            if abs(row[0]["cy"] - b["cy"]) < row_tol:
                row.append(b)
                placed = True
                break
        if not placed:
            rows.append([b])
    ordered = []
    for row in rows:
        row.sort(key=lambda b: b["cx"])
        ordered.extend(row)

    paths = []
    for idx, b in enumerate(ordered):
        contours, _ = cv2.findContours(b["mask"], cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        d_parts = []
        for cnt in contours:
            if len(cnt) < 3:
                continue
            cnt = cv2.approxPolyDP(cnt, 0.6, True)
            d = "M " + " L ".join(f"{p[0][0]},{p[0][1]}" for p in cnt) + " Z"
            d_parts.append(d)
        if not d_parts:
            continue
        d_attr = " ".join(d_parts)
        paths.append(f'<path d="{d_attr}" fill-rule="evenodd" class="ink-piece" style="animation-delay:{idx * 220}ms"/>')

    svg = f'<svg viewBox="0 0 {w} {h}">' + "".join(paths) + "</svg>"
    return {"svg": svg, "piece_count": len(paths), "width": w, "height": h}
