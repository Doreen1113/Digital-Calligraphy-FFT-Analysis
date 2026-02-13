import numpy as np
from numpy.fft import fft, ifft
import re
import pygame, math
from pygame.locals import *
import colorsys
import datetime
import re, math, pygame
from pygame.locals import *

def fftProcess(svg_filename: str, n_coeffs: int = 50):
    """解析 SVG 並執行傅立葉轉換，回傳所有筆劃的係數與全域中心"""
    with open(svg_filename, "r") as f:
        content = f.read()
    
    paths = re.findall(r'\bd="(.*?)"', content)
    all_pts = []
    for path in paths:
        nums = re.findall(r"-?\d+\.?\d*", path)
        for i in range(0, len(nums), 2):
            all_pts.append((float(nums[i]), float(nums[i+1])))
    
    if not all_pts: return [], (0, 0)
    
    # 計算全域 Bounding Box 中心，確保多筆劃對齊
    center_x = (max(p[0] for p in all_pts) + min(p[0] for p in all_pts)) / 2
    center_y = (max(p[1] for p in all_pts) + min(p[1] for p in all_pts)) / 2

    all_segments_fourier = []
    for path in paths:
        nums = re.findall(r"-?\d+\.?\d*", path)
        segment = [(float(nums[i]), float(nums[i+1])) for i in range(0, len(nums), 2)]
        if len(segment) < 5: continue

        # 座標轉複數並平移至中心
        y = np.array([complex(p[0] - center_x, p[1] - center_y) for p in segment])
        N = len(y)
        yy = fft(y)

        # 低通濾波：只保留 n_coeffs 個係數
        if n_coeffs and n_coeffs < N:
            half = n_coeffs // 2
            yy[half : N - half] = 0

        # 轉換為 (振幅, 頻率, 相位)
        # 將頻率索引轉為有號頻率 (負頻率對應到 index > N/2)
        PP = []
        for i, v in enumerate(yy):
            freq = i if i <= N//2 else i - N
            amp = abs(v) / N
            phase = np.angle(v)
            PP.append([amp, freq, phase])
        # 不對係數排序 — 保留原始頻率分佈以對應 IFFT 重建
        all_segments_fourier.append(PP)

    return all_segments_fourier, (center_x, center_y)

def get_reconstructed_points(svg_filename: str, n_coeffs: int = 50):
    """供 GUI 調用：計算重建後的座標點清單"""
    fourier_data, _ = fftProcess(svg_filename, n_coeffs)
    all_strokes = []
    for coeffs in fourier_data:
        N_samples = 300 # 採樣點數
        pts = []
        for t_idx in range(N_samples):
            t = t_idx / N_samples
            val = sum(r * np.exp(1j * (freq * 2 * np.pi * t + phase)) for r, freq, phase in coeffs)
            pts.append((val.real, val.imag))
        all_strokes.append(pts)
    return all_strokes
    
def get_reconstructed_points(svg_filename: str, n_coeffs: int = 50):
    """Parse SVG and for each long path do: FFT -> low-pass filter -> IFFT.
    Return (list_of_point_lists, (minx, maxx, miny, maxy)).
    This preserves original ordering and matches the original shape.
    """
    with open(svg_filename, "r") as f:
        content = f.read()

    # collect all paths and global center like fftProcess
    paths = re.findall(r'\bd="(.*?)"', content)
    all_segments = []
    global_all_pts = []
    for path in paths:
        nums = re.findall(r"-?\d+\.?\d*e?-?\d*?", path)
        pts = []
        for i in range(0, len(nums), 2):
            try:
                x = float(nums[i])
                y = float(nums[i + 1])
            except Exception:
                continue
            pts.append((x, y))
        if pts:
            global_all_pts.extend(pts)

    if not global_all_pts:
        return [], (0, 0, 0, 0)

    xs = [p[0] for p in global_all_pts]
    ys = [p[1] for p in global_all_pts]
    center_x = (max(xs) + min(xs)) / 2
    center_y = (max(ys) + min(ys)) / 2

    all_reconstructed = []
    gminx = gminy = float('inf')
    gmaxx = gmaxy = float('-inf')

    for path in paths:
        nums = re.findall(r"-?\d+\.?\d*e?-?\d*?", path)
        pts = []
        for i in range(0, len(nums), 2):
            try:
                x = float(nums[i])
                y = float(nums[i + 1])
            except Exception:
                continue
            pts.append((x, y))

        if len(pts) < 3:
            continue

        # build complex array centered
        y_complex = np.array([complex(px - center_x, py - center_y) for px, py in pts], dtype=complex)
        N = len(y_complex)
        yy = fft(y_complex)

        # low-pass: zero middle frequencies, keep n_coeffs (head+tail)
        if n_coeffs is not None and 0 < n_coeffs < N:
            half = int(n_coeffs) // 2
            yy[half: N - half] = 0

        rec = ifft(yy)

        rec_pts = [(float(z.real + center_x), float(z.imag + center_y)) for z in rec]

        for x, y in rec_pts:
            gminx = min(gminx, x); gmaxx = max(gmaxx, x)
            gminy = min(gminy, y); gmaxy = max(gmaxy, y)

        all_reconstructed.append(rec_pts)

    return all_reconstructed, (gminx, gmaxx, gminy, gmaxy)
    return all_strokes

# === 2. 動態繪製傅立葉圓周合成圖形 ===
def draw(filename: str, n_coeffs: int = 50, user_scale: float = 1.0):
    # 設定畫布大小 (可以根據需求調整或設為全螢幕)
    WINDOW_W, WINDOW_H = 1200, 800  
    FPS = 60  
    point_size = 1  
    thickness = 2   
    start_xy = (WINDOW_W // 2, WINDOW_H // 2) # 畫面中心
    b_length = 10000 # 軌跡長度

    # 1. 取得傅立葉數據 (使用我們修正後的回傳格式)
    # all_segments: [stroke1_coeffs, stroke2_coeffs, ...]
    # svg_info: (center_x, center_y)
    all_segments, svg_info = fftProcess(filename, n_coeffs=n_coeffs)
    if not all_segments:
        print("Error: No paths found in SVG.")
        return

    # obtain reconstructed bbox from get_reconstructed_points so we can match GUI preview mapping
    try:
        rec_all, bbox = get_reconstructed_points(filename, n_coeffs)
        minx, maxx, miny, maxy = bbox
    except Exception:
        # fallback: derive bbox from original points in fftProcess if needed
        minx = miny = -270
        maxx = maxy = 270

    # 2. 計算縮放比例 (自動適配視窗)
    # 使用與 GUI 相同的映射：base_fit = min(WINDOW_W/svg_w, WINDOW_H/svg_h) * 0.8
    svg_w = max(1.0, maxx - minx)
    svg_h = max(1.0, maxy - miny)
    base_fit = min(WINDOW_W / svg_w, WINDOW_H / svg_h) * 0.8
    final_scale = base_fit * user_scale

    # Center the window on screen and use a fixed-size, non-resizable window
    import os
    os.environ.setdefault('SDL_VIDEO_CENTERED', '1')
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.DOUBLEBUF)
    pygame.display.set_caption(f"Fourier Calligraphy: {filename} (Coeffs: {n_coeffs})")

    # --- 圓的定義 (修正座標計算邏輯) ---
    class Circle:
        def __init__(self, r, freq, phase, color, father=None):
            self.r = r  
            self.freq = freq      # 頻率 (對應原本的 angle_v)
            self.phase = phase    # 初始相位 (對應原本的 angle)
            self.color = color      
            self.father = father  
            self.x, self.y = 0, 0
            self.current_t = 0    # 追蹤時間進度

        def update(self, t, anim_center):
            # 傅立葉合成公式: r * exp(i * (2*pi*f*t + phase))
            # 注意：t 必須正規化為 0~1 之間，或者直接使用角速度
            angle = self.freq * 2 * math.pi * t + self.phase
            
            if self.father:
                self.x = self.father.x + self.r * math.cos(angle) * final_scale
                self.y = self.father.y + self.r * math.sin(angle) * final_scale
            else:
                # 最外層的圓心固定在畫面中央
                # anim_center is computed per-frame to account for window/fullscreen size
                self.x, self.y = anim_center

        def draw(self, screen, show_circles=True, scale=1.0):
            if not self.father: return
            
            if show_circles:
                # 畫輔助圓與連線 (顏色稍微調暗)
                alpha_color = tuple(map(lambda x: x // 4, self.color))
                center = (int(self.father.x), int(self.father.y))
                radius = max(int(abs(self.r) * scale), 1)
                pygame.draw.circle(screen, alpha_color, center, radius, 1)
                pygame.draw.line(screen, self.color, center, (self.x, self.y), 1)
            
            # 畫圓心點
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), point_size)

    # --- 單一筆劃繪製器 ---
    class PathDrawer:
        def __init__(self, fourier_list, color):
            self.circles = []
            self.points = []
            self.color = color
            self.t = 0.0
            
            # 建立圓圈鏈
            # 第一個圓是靜止的中心點
            root = Circle(0, 0, 0, color)
            self.circles.append(root)
            
            for p in fourier_list:
                # p = [amplitude, frequency, phase]
                c = Circle(p[0], p[1], p[2], color, father=self.circles[-1])
                self.circles.append(c)

        def step(self, screen, dt, anim_center, scale):
            self.t += dt
            if self.t > 1.0: self.t = 0 # 循環繪製
            
            # 更新所有圓的位置
            for c in self.circles:
                c.update(self.t, anim_center)
                c.draw(screen, True, scale)
            
            # 紀錄末端點軌跡
            tail = self.circles[-1]
            self.points.append((tail.x, tail.y))
            
            # 限制軌跡長度，避免記憶體溢出
            if len(self.points) > b_length:
                self.points.pop(0)
            
            # 畫出軌跡 (書法線條)
            if len(self.points) > 2:
                pygame.draw.lines(screen, self.color, False, self.points, thickness)

    # --- 初始化筆劃 ---
    drawers = []
    for idx, segment in enumerate(all_segments):
        hue = idx / len(all_segments)
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
        color = (int(r * 255), int(g * 255), int(b * 255))
        drawers.append(PathDrawer(segment, color))

    clock = pygame.time.Clock()
    running = True
    
    # 動畫速度設定 (dt 越小畫得越慢、越精細)
    dt = 1.0 / (FPS * 5) # 5秒畫完一個循環

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE: running = False
                elif event.key == K_s:
                    # 截圖功能保持不變...
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    pygame.image.save(screen, f"result_{timestamp}.png")

        screen.fill((20, 20, 20)) # 深灰色背景更有專業感

        # Fixed center based on the fixed window size so animation matches GUI preview
        anim_cx = WINDOW_W / 2.0 + (svg_info[0] - (minx + maxx) / 2.0) * final_scale
        anim_cy = WINDOW_H / 2.0 + (svg_info[1] - (miny + maxy) / 2.0) * final_scale
        anim_center = (anim_cx, anim_cy)

        for drawer in drawers:
            drawer.step(screen, dt, anim_center, final_scale)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


def debug_compare(filename: str, n_coeffs: int = 50, stroke_idx: int = 0, t_samples=None, out_file: str = "debug_compare.txt"):
    """Compare points from get_reconstructed_points and direct Fourier synthesis at several t values.
    Writes results to out_file for inspection.
    """
    if t_samples is None:
        t_samples = [0.0, 0.25, 0.5, 0.75]

    # get fourier coefficients and center
    fourier_data, center = fftProcess(filename, n_coeffs)
    cx, cy = center

    # get reconstructed points (per-path lists)
    rec_all, _ = get_reconstructed_points(filename, n_coeffs)

    if not fourier_data or stroke_idx >= len(fourier_data) or stroke_idx >= len(rec_all):
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write("Error: stroke index out of range or no data.\n")
        return

    coeffs = fourier_data[stroke_idx]
    rec_pts = rec_all[stroke_idx]

    lines = []
    lines.append(f"Debug compare for {filename}, stroke {stroke_idx}, n_coeffs={n_coeffs}\n")
    for t in t_samples:
        # synth via fourier coefficients (same formula as animation)
        val = sum(c[0] * np.exp(1j * (c[1] * 2 * np.pi * t + c[2])) for c in coeffs)
        synth_x = float(val.real + cx)
        synth_y = float(val.imag + cy)

        # choose index in rec_pts corresponding to t
        idx = int(t * len(rec_pts)) % len(rec_pts)
        rec_x, rec_y = rec_pts[idx]

        dx = rec_x - synth_x
        dy = rec_y - synth_y
        dist = math.hypot(dx, dy)

        lines.append(f"t={t:.3f}: synth=({synth_x:.3f},{synth_y:.3f}), rec_idx={idx}, rec=({rec_x:.3f},{rec_y:.3f}), delta={dist:.6f}\n")

    with open(out_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Wrote debug compare to {out_file}")