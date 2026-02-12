import cv2
import matplotlib.pyplot as plt
import numpy as np
from xml.dom import minidom as md
from queue import Queue
import warnings
from typing import Iterable, List, Tuple, Union

def length_within_points(a: Iterable, empty_value: Union[int, float] = 0) -> int:
    """
    計算非空值區間長度
    """
    a = list(a)
    l_pivot, r_pivot = -1, -2
    for index, (l_val, r_val) in enumerate(zip(a[::1], a[::-1])):
        if l_val != empty_value and l_pivot == -1:
            l_pivot = index
        if r_val != empty_value and r_pivot == -2:
            r_pivot = len(a) - index
    return r_pivot - l_pivot + 1

def is_clockwise(contour: np.ndarray) -> bool:
    """
    判斷輪廓是否為順時針方向
    """
    return cv2.contourArea(contour, oriented=True) < 0

def dump_rings_from_image(
    image: np.ndarray, output_path: str,
    plot_dict: dict = {"color": "k", "linewidth": 2.0},
    default_height: float = 8
) -> List[np.ndarray]:
    """
    從影像中擷取輪廓並繪製成SVG
    """
    blur = cv2.GaussianBlur(image, (3, 3), 0) # 高斯模糊
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY) # 轉灰階
    edge = cv2.Canny(gray, 50, 150) # Canny邊緣檢測
    edge = cv2.GaussianBlur(edge, (3, 3), 0) # 再次模糊

    valid_width = length_within_points(edge.sum(axis=0))
    valid_height = length_within_points(edge.sum(axis=1))
    true_ratio = valid_width / valid_height

    contour_tuple = cv2.findContours(edge, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
    contours = contour_tuple[0]

    MIN_CONTOUR_LENGTH = 0.5
    rings = []

    for c in contours:
        if len(c) < MIN_CONTOUR_LENGTH:
            continue
        if not is_clockwise(c): # 避免內部重複輪廓
            continue
        rings.append(np.array(c).reshape([-1, 2]))

    max_x, max_y, min_x, min_y = 0, 0, 0, 0
    for ring in rings:
        max_x = max(max_x, ring.max(axis=0)[0])
        max_y = max(max_y, ring.max(axis=0)[1])
        min_x = max(min_x, ring.min(axis=0)[0])
        min_y = max(min_y, ring.min(axis=0)[1])

    plt.figure(figsize=[default_height * true_ratio, default_height])

    for ring in rings:
        xx = ring[..., 0]
        yy = max_y - ring[..., 1]
        plt.plot(xx, yy, **plot_dict)

    plt.axis("off")
    plt.savefig(output_path)

def remove_matplotlib_background(svg_file: str, bg_node_name: str = "patch_1") -> None:
    """
    移除SVG中matplotlib自動產生的背景節點
    """
    dom_tree: md.Document = md.parse(svg_file)
    svg_node = None
    for node in dom_tree.childNodes:
        if node.nodeName == "svg":
            svg_node: md.Element = node
    if svg_node is None:
        raise ValueError(f"SVG node not found in {svg_file}")

    q = Queue()
    q.put(svg_node)
    target_node = None
    while not q.empty():
        cur: md.Node = q.get()
        if cur.hasChildNodes():
            for node in cur.childNodes:
                q.put(node)
        if hasattr(cur, "getAttribute"):
            if cur.getAttribute("id") == bg_node_name:
                target_node = cur

    if target_node is None:
        warnings.warn("Background node not found (OK if already removed)")
    else:
        target_node.parentNode.removeChild(target_node)

    with open(svg_file, "w", encoding="utf-8") as fp:
        dom_tree.writexml(writer=fp, indent="\t")

def bitmap_to_contour_svg(input_bitmap_path: str, output_svg_path: str):
    """
    將位圖轉換為SVG輪廓檔
    """
    image = cv2.imread(input_bitmap_path)
    dump_rings_from_image(image, output_path=output_svg_path)
    remove_matplotlib_background(output_svg_path)
