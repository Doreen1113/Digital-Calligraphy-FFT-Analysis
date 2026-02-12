import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from SVG import bitmap_to_contour_svg
from fft import draw
from opencvUtils import *

class InteractiveWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fname = None

        # 視窗設定
        self.setWindowTitle("Visiable FFT image")
        self.resize(500, 500)

        # 主布局
        self.layout_main = QHBoxLayout()
        self.layoutLeft = QFormLayout()
        self.layoutRight = QFormLayout()

        self.leftForm()
        self.rightForm()

        self.layout_main.addLayout(self.layoutLeft)
        self.layout_main.addLayout(self.layoutRight)

        self.setLayout(self.layout_main)

    def leftForm(self):
        # 左側表單，包含邊緣檢測方法選擇與按鈕
        self.edgeProcessingMethodChoose = QComboBox()
        self.edgeProcessingMethodChoose.addItems(["Canny", "Sobel", "Laplacian", "Scharr"])

        # 對應方法字典
        self.edgeProcessingMethod = {
            "Canny": Canny,
            "Sobel": Sobel,
            "Scharr": Scharr,
            "Laplacian": Laplacian,
        }

        self.layoutLeft.addRow("圖片邊緣化方式", self.edgeProcessingMethodChoose)

        # 導入圖片按鈕
        self.button_1 = QPushButton("導入圖片")
        self.button_1.clicked.connect(self.loadPicture)

        # 處理圖片按鈕
        self.button_2 = QPushButton("處理圖片")
        self.button_2.clicked.connect(self.processImage)

        # 生成結果按鈕
        self.button_3 = QPushButton("生成结果")
        self.button_3.clicked.connect(self.fftImageProcess)

        self.layoutLeft.addWidget(self.button_1)
        self.layoutLeft.addWidget(self.button_2)
        self.layoutLeft.addWidget(self.button_3)

    def rightForm(self):
        # 右側顯示圖片區域
        self.picture = QLabel()
        self.layoutRight.addWidget(self.picture)

    def loadPicture(self):
        """
        從電腦選擇圖片檔案
        """
        self.fname, _ = QFileDialog.getOpenFileName(
            self, "選擇圖片", "C:\\Users\\ASUS\\Downloads\\image-FFT-main\\examples", "Image files(*.jpg *.gif *.png *.jpeg *.svg)"
        )

        if self.fname == "":
            self.fname = None
            return

        # 顯示圖片
        self.picture.setPixmap(QPixmap(self.fname))

    def processImage(self):
        """
        使用選擇的邊緣檢測方法處理圖片
        """
        if self.fname is None:
            msg_box = QMessageBox()
            msg_box.setText("請先導入圖片")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return

        processMethod = self.edgeProcessingMethod[self.edgeProcessingMethodChoose.currentText()]
        self.processed_img = processMethod(self.fname)

        # 顯示處理後圖片
        self.picture.setPixmap(QPixmap(self.processed_img))

    def fftImageProcess(self):
        """
        生成SVG並啟動傅立葉繪圖
        """
        if self.fname is None:
            msg_box = QMessageBox()
            msg_box.setText("請先導入圖片")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return

        self.svg_name = f"./images/{self.fname.split('/')[-1].split('.')[0]}.svg"

        self.processImage()

        # 若非SVG檔，轉換成SVG
        if self.fname.split(".")[-1] != "svg":
            bitmap_to_contour_svg(self.processed_img, self.svg_name)
        else:
            self.svg_name = self.fname

        # 顯示SVG
        self.picture.setPixmap(QPixmap(self.svg_name))

        # 啟動傅立葉繪圖
        draw(self.svg_name)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tool = InteractiveWindow()
    tool.show()
    sys.exit(app.exec_())
