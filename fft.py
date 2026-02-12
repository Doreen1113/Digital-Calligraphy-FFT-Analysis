import numpy as np
from numpy.fft import fft
import re
from typing import List
import pygame, math
from pygame.locals import *
import colorsys
import datetime  # 加入時間戳用

# === 1. 解析SVG路徑並做傅立葉轉換 ===
def fftProcess(svg_filename: str) -> List[List[List[float]]]:
    with open(svg_filename, "r") as f:
        content = f.read()
        # 從SVG檔案中找出所有路徑d屬性
        paths = re.findall(r'\bd="(.*?)"', content)
        all_segments = []

        for path in paths:
            # 解析路徑中的所有數字點座標
            points = re.findall(r"-?\d+\.?\d*e?-?\d*?", path)
            segment = []
            # 每兩個數字為一個(x, y)座標
            for i in range(0, len(points), 2):
                segment.append((float(points[i + 1]), float(points[i])))

            # 忽略點數過少的路徑
            if len(segment) < 10:
                continue

            # 將座標轉為複數，並做中心平移
            y = [complex(p[0] - 270, p[1] - 270) for p in segment]
            y_len = len(y)
            # 對座標序列做傅立葉轉換
            yy = fft(y)

            PP = []
            for i, v in enumerate(yy[:y_len]):
                c = -2 * np.pi * i / y_len  # 角速度
                # 拆成實部與虛部，並分別存入
                PP.append([-v.real / y_len, c, -np.pi / 2])
                PP.append([-v.imag / y_len, c, np.pi])

            # 依據振幅大小排序
            PP.sort(key=lambda x: abs(x[0]), reverse=True)
            all_segments.append(PP)

    return all_segments

# === 2. 動態繪製傅立葉圓周合成圖形 ===
def draw(filename: str):
    WINDOW_W, WINDOW_H = 1920, 1080  
    one_time = 10
    scale = 1
    FPS = 60  # 幀率
    point_size = 1  # 圓心點大小
    thickness = 2   # 筆劃粗細
    start_xy = (WINDOW_W // 4, WINDOW_H // 2)  # 起始座標
    b_length = 8000  # 筆劃軌跡長度上限

    all_segments = fftProcess(filename)  # 取得所有筆畫的傅立葉係數

    pygame.init()
    # 建立繪圖視窗
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.DOUBLEBUF | pygame.RESIZABLE, 32)
    pygame.display.set_caption("傅立葉多筆畫繪圖")

    # --- 內部類別：圓的定義 ---
    class Circle:
        def __init__(self, r, angle_v, angle, color, father=None):
            self.r = r  
            self.angle_v = angle_v  # 角速度
            self.angle = angle      # 當前角度
            self.color = color     
            self.father = father    # 父圓
            self.x, self.y = 0, 0  # 圓心座標

        def set_xy(self, xy):
            self.x, self.y = xy

        def set_xy_by_angle(self):
            # 根據父圓與角度計算圓心座標
            self.x = self.father.x + self.r * math.cos(self.angle) * scale
            self.y = self.father.y + self.r * math.sin(self.angle) * scale

        def run(self, step_time):
            # 旋轉圓，更新角度與位置
            if self.father:
                self.angle += self.angle_v * step_time
                self.set_xy_by_angle()

        def draw(self, screen):
            # 畫圓心點
            color_an = tuple(map(lambda x: x // 3, self.color))
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), point_size)
            # 畫圓與連線
            if self.father:
                pygame.draw.circle(screen, color_an, (int(self.father.x), int(self.father.y)), max(int(abs(self.r) * scale), 1), 1)
                pygame.draw.line(screen, self.color, (self.father.x, self.father.y), (self.x, self.y), 1)

    # --- 內部類別：單一路徑的傅立葉合成與繪製 ---
    class PathDrawer:
        def __init__(self, fourier_list, color):
            self.circles = []
            self.points = []
            self.color = color
            # 建立最外層圓心
            super_circle = Circle(0, 0, 0, color)
            super_circle.set_xy(start_xy)
            self.circles = [super_circle]

            # 依據傅立葉係數建立圓
            for i, p in enumerate(fourier_list):
                c = Circle(p[0], p[1], p[2], color, father=self.circles[i])
                self.circles.append(c)

        def run_and_draw(self, screen):
            # 更新所有圓並繪製
            for c in self.circles:
                c.run(1)
                c.draw(screen)
            tail = self.circles[-1]
            self.points.append((tail.x, tail.y))
            # 控制軌跡長度
            if len(self.points) > b_length:
                self.points.pop(0)
            # 畫出筆劃軌跡
            for i in range(len(self.points) - 1):
                pygame.draw.line(screen, self.color, self.points[i], self.points[i + 1], thickness)

    # --- 建立所有筆畫的PathDrawer ---
    drawers = []
    for idx, segment in enumerate(all_segments):
        # 每條筆畫給不同顏色
        hue = idx / len(all_segments)
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        color = (int(r * 255), int(g * 255), int(b * 255))
        drawers.append(PathDrawer(segment, color))

    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    # 直接儲存目前完整畫面（含圓）
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"final_screen_{timestamp}.png"
                    pygame.image.save(screen, filename)
                    print(f"畫面已儲存：{filename}")
                    pygame.quit()
                    return

                elif event.key == K_s:
                    # 儲存純筆劃（不含圓）版本
                    screen.fill((0, 0, 0))
                    for drawer in drawers:
                        for i in range(len(drawer.points) - 1):
                            pygame.draw.line(screen, drawer.color, drawer.points[i], drawer.points[i + 1], thickness)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"final_strokes_{timestamp}.png"
                    pygame.image.save(screen, filename)
                    print(f"純筆劃畫面已儲存：{filename}")

        # 每幀刷新畫面
        screen.fill((0, 0, 0))
        for drawer in drawers:
            drawer.run_and_draw(screen)

        pygame.display.update()
        clock.tick(FPS)
