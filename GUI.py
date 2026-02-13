import os
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 匯入專案自定義模組
from SVG import bitmap_to_contour_svg
from Preprocessing import clean_image  # 這是你之前上傳的智慧預處理
import fft

class InteractiveWindow(QWidget):
    def __init__(self, init_coeffs=50):
        super().__init__()
        self.fname = None
        self.svg_name = None
        self.processed_img_path = "./images/temp_clean.png" # 預處理後的暫存檔
        self.preview_bbox = None
        self.preview_strokes = None
        
        # 設定畫布基準大小（與 Pygame 動畫同步）
        self.anim_view_w = 1200
        self.anim_view_h = 800
        
        self.initUI(init_coeffs)

    def initUI(self, init_coeffs):
        self.setWindowTitle("Digital-Calligraphy-FFT-Analysis (Smart Version)")
        self.resize(1550, 880) 
        
        main_layout = QHBoxLayout(self)
        
        # --- 左側控制面板 ---
        left_panel = QVBoxLayout()
        left_form = QFormLayout()
        
        # 參數滑桿：修復平滑度 (傅立葉係數數量)
        self.slider_fft = QSlider(Qt.Horizontal)
        self.slider_fft.setRange(1, 100)
        self.slider_fft.setValue(init_coeffs)
        self.label_fft = QLabel(f"修復平滑度: {init_coeffs}")
        
        # 參數滑桿：預覽縮放
        self.slider_scale = QSlider(Qt.Horizontal)
        self.slider_scale.setRange(10, 100)
        self.slider_scale.setValue(100)
        self.label_scale = QLabel("預覽縮放: 100%")
        
        # 按鈕群組
        btn_load = QPushButton("1. 導入圖片 (智慧預處理)")
        btn_load.clicked.connect(self.loadImg)
        btn_load.setMinimumHeight(40)
        
        btn_gen = QPushButton("2. 生成傅立葉結構")
        btn_gen.clicked.connect(self.genResult)
        btn_gen.setMinimumHeight(40)
        
        btn_anim = QPushButton("3. 啟動動畫 (Pygame 同步)")
        btn_anim.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_anim.clicked.connect(self.runAnim)
        btn_anim.setMinimumHeight(50)

        left_form.addRow(QLabel("<b><font size='4'>核心參數設定</font></b>"))
        left_form.addRow(self.label_fft, self.slider_fft)
        left_form.addRow(self.label_scale, self.slider_scale)
        
        left_panel.addLayout(left_form)
        left_panel.addSpacing(20)
        left_panel.addWidget(btn_load)
        left_panel.addWidget(btn_gen)
        left_panel.addSpacing(10)
        left_panel.addWidget(btn_anim)
        left_panel.addStretch() 
        
        # --- 右側預覽畫布 ---
        self.view = QLabel("等待導入圖片...")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setFixedSize(self.anim_view_w, self.anim_view_h)
        self.view.setStyleSheet("""
            background: #f0f0f0; 
            border: 3px solid #2c3e50; 
            border-radius: 10px;
            font-weight: bold;
            color: #7f8c8d;
        """)
        
        main_layout.addLayout(left_panel, 1)
        main_layout.addWidget(self.view)
        
        # 連結訊號
        self.slider_fft.valueChanged.connect(self.updateUI)
        self.slider_scale.valueChanged.connect(self.updateUI)

    def updateUI(self):
        self.label_fft.setText(f"修復平滑度: {self.slider_fft.value()}")
        self.label_scale.setText(f"預覽縮放: {self.slider_scale.value()}%")
        self.livePreview()

    def loadImg(self):
        self.fname, _ = QFileDialog.getOpenFileName(self, "選取書法圖片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if self.fname:
            if not os.path.exists("./images"): os.makedirs("./images")
            
            # --- 智慧預處理 (核心步驟) ---
            # 呼叫 Preprocessing/__init__.py 裡的 clean_image
            # 這會自動執行：中值去噪 -> 背景極性偵測 -> 自動黑白反轉
            binary_img = clean_image(self.fname)
            
            if binary_img is not None:
                import cv2
                cv2.imwrite(self.processed_img_path, binary_img)
                # 顯示預處理後的結果
                pix = QPixmap(self.processed_img_path).scaled(self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.view.setPixmap(pix)
                self.view.setStyleSheet("background: white; border: 3px solid #2c3e50; border-radius: 10px;")
                QMessageBox.information(self, "預處理成功", "已自動偵測背景並完成二值化與去噪。")

    def genResult(self):
        if not self.fname:
            QMessageBox.warning(self, "錯誤", "請先導入圖片")
            return
        
        self.svg_name = "./images/temp.svg"
        # 根據預處理後的圖生成向量輪廓
        bitmap_to_contour_svg(self.processed_img_path, self.svg_name)
        
        # 取得重建點與邊界資訊
        res = fft.get_reconstructed_points(self.svg_name, self.slider_fft.value())
        if isinstance(res, tuple) and len(res) == 2:
            self.preview_strokes, self.preview_bbox = res
        else:
            self.preview_strokes = res
            self.preview_bbox = None
        
        self.livePreview()

    def livePreview(self):
        if not self.svg_name: return
        
        # 即時重新計算傅立葉重建點
        res = fft.get_reconstructed_points(self.svg_name, self.slider_fft.value())
        strokes = res[0] if isinstance(res, tuple) else res
        scale_user = self.slider_scale.value() / 100.0
        
        # 建立畫布
        pix = QPixmap(self.anim_view_w, self.anim_view_h)
        pix.fill(Qt.white)
        
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.black, 2))
        
        # 畫布中心點
        cx, cy = self.anim_view_w / 2, self.anim_view_h / 2

        if self.preview_bbox:
            minx, maxx, miny, maxy = self.preview_bbox
            bbox_cx = (minx + maxx) / 2.0
            bbox_cy = (miny + maxy) / 2.0
            
            # 適配縮放比例
            svg_w = max(1.0, maxx - minx)
            svg_h = max(1.0, maxy - miny)
            base_fit = min(self.anim_view_w / svg_w, self.anim_view_h / svg_h) * 0.8
            final_scale = base_fit * scale_user
        else:
            bbox_cx, bbox_cy = 0.0, 0.0
            final_scale = scale_user

        # 渲染所有筆劃 (包含內部結構)
        for s in strokes:
            if not s or len(s) < 2: continue
            for i in range(len(s)-1):
                x1 = cx + (s[i][0] - bbox_cx) * final_scale
                y1 = cy + (s[i][1] - bbox_cy) * final_scale
                x2 = cx + (s[i+1][0] - bbox_cx) * final_scale
                y2 = cy + (s[i+1][1] - bbox_cy) * final_scale
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        painter.end()
        self.view.setPixmap(pix)

    def runAnim(self):
        if not self.svg_name:
            QMessageBox.warning(self, "提示", "請先生成傅立葉結構")
            return
        # 啟動 Pygame 動畫，同步目前的滑桿參數
        fft.draw(self.svg_name, self.slider_fft.value(), self.slider_scale.value()/100.0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InteractiveWindow()
    window.show()
    sys.exit(app.exec_())