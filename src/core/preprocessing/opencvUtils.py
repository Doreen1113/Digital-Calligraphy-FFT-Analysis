import cv2
from cv2 import findContours

def Sobel(name):
    """
    使用Sobel算子進行邊緣檢測
    """
    image = cv2.imread(name, cv2.IMREAD_GRAYSCALE) # 讀取灰階圖
    sobxel_h = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3) # 水平邊緣
    sobxel_h = cv2.convertScaleAbs(sobxel_h) # 轉換為8位元圖像
    sobxel_v = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3) # 垂直邊緣
    sobxel_v = cv2.convertScaleAbs(sobxel_v)
    Sobel_all = cv2.addWeighted(sobxel_h, 0.5, sobxel_v, 0.5, 0) # 合成邊緣圖
    return savePicture(name, Sobel.__name__, Sobel_all)

def Scharr(name):
    """
    使用Scharr算子進行邊緣檢測
    """
    image = cv2.imread(name, cv2.IMREAD_GRAYSCALE) # 讀取灰階圖
    scharrx = cv2.Scharr(image, cv2.CV_64F, 1, 0) # 水平邊緣
    scharry = cv2.Scharr(image, cv2.CV_64F, 0, 1) # 垂直邊緣
    scharrx = cv2.convertScaleAbs(scharrx)
    scharry = cv2.convertScaleAbs(scharry)
    Scharr_all = cv2.addWeighted(scharrx, 0.5, scharry, 0.5, 0) # 合成邊緣圖
    return savePicture(name, Scharr.__name__, Scharr_all)

def Laplacian(name):
    """
    使用Laplacian算子進行邊緣檢測
    """
    image = cv2.imread(name, cv2.IMREAD_GRAYSCALE) # 讀取灰階圖
    laplacian = cv2.Laplacian(image, cv2.CV_64F) # 計算拉普拉斯
    laplacian = cv2.convertScaleAbs(laplacian) # 轉換為8位元圖像
    return savePicture(name, Laplacian.__name__, laplacian)

def Canny(name):
    """
    使用Canny邊緣檢測
    """
    image = cv2.imread(name, cv2.IMREAD_GRAYSCALE) # 讀取灰階圖
    conny = cv2.Canny(image, 100, 200) # Canny邊緣檢測
    return savePicture(name, Canny.__name__, conny)

def FindContours(image):
    """
    找出輪廓並繪製
    """
    ret, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    draw_image = image.copy()
    newImage = cv2.drawContours(draw_image, contours, -1, (0, 0, 255), 2)
    return newImage

class GaussPyramid:
    """
    高斯金字塔上下採樣
    """
    def __init__(self, name) -> None:
        self.name = name
        self.image = cv2.imread(name, cv2.IMREAD_GRAYSCALE) # 讀取灰階圖

    def up(self):
        newImage = cv2.pyrUp(self.image) # 上採樣
        return savePicture(self.name, "GaussPyramidUp", newImage)

    def down(self):
        newImage = cv2.pyrDown(self.image) # 下採樣
        return savePicture(self.name, "GaussPyramidDown", newImage)

def savePicture(name, functionName, image):
    """
    儲存處理後的圖片到./images資料夾
    """
    newPictureName = f"./images/{name.split('/')[-1].split('.')[0]}_{functionName}.png"
    cv2.imwrite(newPictureName, image)
    return newPictureName
