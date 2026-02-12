from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from SVG import bitmap_to_contour_svg
import fft
import os

class InteractiveWindow(QWidget):
    def __init__(self, init_coeffs=200):
        super().__init__()
        self.fname = None
        self.svg_name = None
        self.preview_bbox = None
        self.preview_strokes = None
        
        # 設定動畫視窗的基準大小
        self.anim_view_w = 1200
        self.anim_view_h = 800
        
        self.setWindowTitle("Digital-Calligraphy-FFT-Analysis")
        # 調整主視窗大小以容納 1200x800 的預覽區加上左側面板
        self.resize(1550, 850) 
        
        layout = QHBoxLayout(self)
        left_panel = QVBoxLayout()
        left_form = QFormLayout()
        
        # UI 元件
        self.slider_fft = QSlider(Qt.Horizontal)
        self.slider_fft.setRange(5, 1000) # 擴大範圍以觀察修復效果
        self.slider_fft.setValue(init_coeffs)
        
        self.slider_scale = QSlider(Qt.Horizontal)
        self.slider_scale.setRange(10, 500)
        self.slider_scale.setValue(100)
        
        self.label_fft = QLabel(f"修復平滑度: {init_coeffs}")
        self.label_scale = QLabel("預覽縮放: 100%")
        
        btn_load = QPushButton("1. 導入圖片")
        btn_load.clicked.connect(self.loadImg)
        btn_gen = QPushButton("2. 生成結果 (預覽)")
        btn_gen.clicked.connect(self.genResult)
        btn_anim = QPushButton("3. 啟動動畫 (Pygame)")
        btn_anim.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_anim.clicked.connect(self.runAnim)

        left_form.addRow(QLabel("<b>參數設定</b>"))
        left_form.addRow(self.label_fft, self.slider_fft)
        left_form.addRow(self.label_scale, self.slider_scale)
        left_panel.addLayout(left_form)
        left_panel.addWidget(btn_load)
        left_panel.addWidget(btn_gen)
        left_panel.addWidget(btn_anim)
        left_panel.addStretch() # 將按鈕向上推
        
        # 關鍵修改：固定預覽區大小，使其永遠等於動畫視窗大小
        self.view = QLabel("預覽區 (1200x800)")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setFixedSize(self.anim_view_w, self.anim_view_h)
        self.view.setStyleSheet("background: white; border: 2px solid #333; border-radius: 5px;")
        
        layout.addLayout(left_panel, 1)
        layout.addWidget(self.view) # 不再使用 stretch，因為大小已固定
        
        self.slider_fft.valueChanged.connect(self.updateUI)
        self.slider_scale.valueChanged.connect(self.updateUI)

    def updateUI(self):
        self.label_fft.setText(f"修復平滑度: {self.slider_fft.value()}")
        self.label_scale.setText(f"預覽縮放: {self.slider_scale.value()}%")
        self.livePreview()

    def loadImg(self):
        self.fname, _ = QFileDialog.getOpenFileName(self, "選圖片", "", "Images (*.png *.jpg *.jpeg)")
        if self.fname:
            # 初始導入時先縮放適配 QLabel 顯示
            pix = QPixmap(self.fname).scaled(self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.view.setPixmap(pix)

    def genResult(self):
        if not self.fname: return
        if not os.path.exists("./images"): os.makedirs("./images")
        self.svg_name = "./images/temp.svg"
        bitmap_to_contour_svg(self.fname, self.svg_name)
        
        # 取得初始重建點與 Bounding Box
        res = fft.get_reconstructed_points(self.svg_name, self.slider_fft.value())
        if isinstance(res, tuple) and len(res) == 2:
            self.preview_strokes, self.preview_bbox = res
        else:
            self.preview_strokes = res
            self.preview_bbox = None
        self.livePreview()

    def livePreview(self):
        if not self.svg_name: return
        
        # 每次滑桿變動時重新計算重建點
        res = fft.get_reconstructed_points(self.svg_name, self.slider_fft.value())
        strokes = res[0] if isinstance(res, tuple) else res

        scale_user = self.slider_scale.value() / 100.0
        
        # 建立一個固定 1200x800 的畫布
        pix = QPixmap(self.anim_view_w, self.anim_view_h)
        pix.fill(Qt.white)
        
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.black, 2))
        
        # 中心點固定為預覽畫布的幾何中心
        cx, cy = self.anim_view_w / 2, self.anim_view_h / 2

        # 使用固定中心點 (Bounding Box Center) 進行座標變換
        if self.preview_bbox:
            minx, maxx, miny, maxy = self.preview_bbox
            bbox_cx = (minx + maxx) / 2.0
            bbox_cy = (miny + maxy) / 2.0
            
            # 計算基礎縮放比例（適配 1200x800），再乘上使用者調整的 scale
            svg_w = max(1.0, maxx - minx)
            svg_h = max(1.0, maxy - miny)
            base_fit = min(self.anim_view_w / svg_w, self.anim_view_h / svg_h) * 0.8
            final_scale = base_fit * scale_user
        else:
            bbox_cx, bbox_cy = 0.0, 0.0
            final_scale = scale_user

        # 繪製筆劃
        for s in strokes:
            if not s or len(s) < 2: continue
            for i in range(len(s)-1):
                # 座標變換邏輯：(原始座標 - 中心) * 縮放 + 畫布中心
                x1 = cx + (s[i][0] - bbox_cx) * final_scale
                y1 = cy + (s[i][1] - bbox_cy) * final_scale
                x2 = cx + (s[i+1][0] - bbox_cx) * final_scale
                y2 = cy + (s[i+1][1] - bbox_cy) * final_scale
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        painter.end()
        self.view.setPixmap(pix)

    def runAnim(self):
        if not self.svg_name:
            QMessageBox.warning(self, "提示", "請先生成結果")
            return
        # 啟動動畫時，參數與預覽完全同步
        fft.draw(self.svg_name, self.slider_fft.value(), self.slider_scale.value()/100.0)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = InteractiveWindow()
    window.show()
    sys.exit(app.exec_())