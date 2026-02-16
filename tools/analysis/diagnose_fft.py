"""
FFT 特徵診斷工具
檢查 FFT 係數與特徵計算是否正常
"""
import os
import sys
import glob
import numpy as np
import cv2
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.preprocessing import clean_image
from src.core.svg import bitmap_to_contour_svg
from src.core import fft
from src.utils import get_config, FontDataLoader


def diagnose_single_image(image_path: str, target_len: int = 50):
    """
    診斷單張圖片的 FFT 處理結果

    Args:
        image_path: 圖片路徑
        target_len: 目標傅立葉係數長度
    """
    print("\n" + "="*70)
    print(f" 診斷圖片: {os.path.basename(image_path)}")
    print("="*70)

    try:
        # 1. 預處理
        print("\n[1] 圖片預處理...")
        binary = clean_image(image_path)
        temp_binary = "./output/temp/diagnose_clean.png"
        os.makedirs(os.path.dirname(temp_binary), exist_ok=True)
        cv2.imwrite(temp_binary, binary)
        print(f"    圖片尺寸: {binary.shape}")

        # 2. SVG 轉換
        print("\n[2] 轉換為 SVG...")
        temp_svg = "./output/temp/diagnose.svg"
        bitmap_to_contour_svg(temp_binary, temp_svg)

        # 檢查 SVG 檔案大小
        svg_size = os.path.getsize(temp_svg)
        print(f"    SVG 檔案大小: {svg_size} bytes")

        # 3. FFT 處理
        print(f"\n[3] FFT 轉換 (目標長度: {target_len})...")
        fourier_data, _ = fft.fftProcess(temp_svg, n_coeffs=target_len + 5)

        if not fourier_data:
            print("    [Error] 沒有 FFT 資料！")
            return

        print(f"    筆畫數: {len(fourier_data)}")

        # 4. 分析每個筆畫
        print("\n[4] 分析各筆畫的 FFT 係數...")
        for stroke_idx, stroke_coeffs in enumerate(fourier_data[:3], 1):  # 只看前 3 個筆畫
            print(f"\n    筆畫 {stroke_idx}:")
            print(f"      係數數量: {len(stroke_coeffs)}")

            if len(stroke_coeffs) < target_len:
                print(f"      [Warning] 係數不足 {target_len} 個！")
                continue

            # 取前 target_len 個係數的振幅
            amps = np.array([max(1e-10, c[0]) for c in stroke_coeffs[:target_len]])

            print(f"      振幅範圍: {amps.min():.6f} ~ {amps.max():.6f}")
            print(f"      前 5 個振幅: {amps[:5]}")
            print(f"      後 5 個振幅: {amps[-5:]}")

            # 計算頻段能量
            total_e = np.sum(amps ** 2) + 1e-10
            low = np.sum(amps[:5] ** 2) / total_e
            mid = np.sum(amps[5:15] ** 2) / total_e
            high = np.sum(amps[15:] ** 2) / total_e

            print(f"\n      能量分布:")
            print(f"        低頻 (0-4):   {low:.6f} ({low*100:.2f}%)")
            print(f"        中頻 (5-14):  {mid:.6f} ({mid*100:.2f}%)")
            print(f"        高頻 (15+):   {high:.6f} ({high*100:.2f}%)")
            print(f"        總和: {low+mid+high:.6f}")

            # 檢查高頻係數
            high_freq_amps = amps[15:]
            print(f"\n      高頻部分 (索引 15-{target_len-1}):")
            print(f"        係數數量: {len(high_freq_amps)}")
            print(f"        平均振幅: {high_freq_amps.mean():.6f}")
            print(f"        最大振幅: {high_freq_amps.max():.6f}")
            print(f"        非零係數: {np.count_nonzero(high_freq_amps > 1e-6)}/{len(high_freq_amps)}")

        # 5. 計算整體平均特徵
        print("\n[5] 計算整體平均特徵...")
        stroke_features = []
        for stroke_coeffs in fourier_data:
            if len(stroke_coeffs) < target_len:
                continue

            amps = np.array([max(1e-10, c[0]) for c in stroke_coeffs[:target_len]])
            total_e = np.sum(amps ** 2) + 1e-10

            low = np.sum(amps[:5] ** 2) / total_e
            mid = np.sum(amps[5:15] ** 2) / total_e
            high = np.sum(amps[15:] ** 2) / total_e

            freqs = np.arange(target_len, dtype=np.float64)
            centroid = np.sum(freqs * amps) / (np.sum(amps) + 1e-10)
            dc_fund_ratio = amps[0] / (amps[1] + 1e-10)
            log_amps = np.log1p(amps)
            slope = np.polyfit(freqs, log_amps, 1)[0]

            if amps[1] > 1e-10:
                decay = np.mean(amps[10:20]) / amps[1]
            else:
                decay = 0.0

            feat = [low, mid, high, centroid / target_len,
                   dc_fund_ratio, abs(slope), decay]
            stroke_features.append(feat)

        if stroke_features:
            avg_feature = np.mean(stroke_features, axis=0)

            print(f"\n    平均特徵向量 (基於 {len(stroke_features)} 個筆畫):")
            feature_names = ['低頻能量', '中頻能量', '高頻能量', '頻譜重心',
                           'DC/基頻比', '頻譜斜率', '高頻衰減率']
            for name, value in zip(feature_names, avg_feature):
                print(f"      {name:12s}: {value:.6f}")

        print("\n" + "="*70)

    except Exception as e:
        print(f"\n[Error] 診斷失敗: {e}")
        import traceback
        traceback.print_exc()


def diagnose_calligrapher(calligrapher_name: str, num_samples: int = 3):
    """
    診斷某位書法家的前 N 張圖片

    Args:
        calligrapher_name: 書法家名稱（英文）
        num_samples: 要診斷的圖片數量
    """
    print("\n" + "="*70)
    print(f" 診斷書法家: {calligrapher_name}")
    print("="*70)

    loader = FontDataLoader()
    config = get_config()

    info = loader.get_calligrapher_info(calligrapher_name)
    if not info:
        print(f"[Error] 找不到書法家: {calligrapher_name}")
        return

    img_dir = info['image_dir']
    img_paths = sorted(glob.glob(os.path.join(img_dir, "*.[pj][np]g")))[:num_samples]

    print(f"\n找到 {len(img_paths)} 張圖片")

    target_len = config.get('fft', 'target_length', default=50)

    for img_path in img_paths:
        diagnose_single_image(img_path, target_len)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='FFT 特徵診斷工具')
    parser.add_argument('--calligrapher', default='zhiyong',
                       help='書法家名稱（英文，如: zhiyong, shen_yinmo）')
    parser.add_argument('--samples', type=int, default=3,
                       help='要診斷的圖片數量')
    parser.add_argument('--image', help='診斷單張圖片（指定完整路徑）')

    args = parser.parse_args()

    if args.image:
        # 診斷單張圖片
        diagnose_single_image(args.image)
    else:
        # 診斷書法家
        diagnose_calligrapher(args.calligrapher, args.samples)
