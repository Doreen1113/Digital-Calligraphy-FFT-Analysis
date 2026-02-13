# style_analyzer.py
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from Preprocessing.cleaner import get_clean_binary
import fft # 呼叫你的 fft.py

def extract_style_features(calligrapher_path):
    # 抓取該名家資料夾內的所有圖片
    images = glob.glob(os.path.join(calligrapher_path, "*.png"))
    all_coeffs = []
    
    for img_p in images[:50]: # 每個名家取 50 字做樣本
        # 1. 預處理
        binary = get_clean_binary(img_p)
        # 2. 透過 FFT 取得傅立葉描述子
        # 假設你的 fft.py 有一個函數能回傳歸一化後的振幅
        coeffs = fft.get_fourier_descriptors(binary, n_coeffs=64)
        all_coeffs.append(coeffs)
    
    return np.mean(all_coeffs, axis=0)

if __name__ == "__main__":
    styles = {
        "Yan_Zhenqing": "./data/Yan_Zhenqing",
        "Liu_Gongquan": "./data/Liu_Gongquan"
    }
    
    plt.figure(figsize=(10, 6))
    for name, path in styles.items():
        if os.path.exists(path):
            avg_feature = extract_style_features(path)
            # 畫出能量分布圖 (排除第0項直流分量)
            plt.plot(avg_feature[1:30], label=f"{name} Spectrum")

    plt.title("Fourier Style Analysis: Yan vs Liu")
    plt.xlabel("Fourier Descriptor Index (Frequency)")
    plt.ylabel("Magnitude (Shape Feature)")
    plt.legend()
    plt.savefig("./output/style_comparison.png")
    plt.show()