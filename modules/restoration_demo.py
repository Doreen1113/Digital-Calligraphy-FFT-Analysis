import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from Preprocessing import clean_image
from SVG import bitmap_to_contour_svg
import fft

# 解決字體顯示問題
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def add_damage(image, damage_type="noise", intensity=0.3, severity="medium"):
    """施加人工損壞壓力測試
    
    Args:
        image: 輸入圖像 (灰度)
        damage_type: 破壞類型 - "noise", "erosion", "occlusion"
        intensity: 破壞強度 (0.0-1.0, 保留向後兼容性)
        severity: 破壞等級 - "light", "medium", "heavy"
    
    Damage Effects:
        - Noise: 椒盐噪声 + 轻微高斯噪声，模拟扫描杂讯和霉点
        - Erosion: 形态学侵蚀，模拟笔画风化和断裂
        - Occlusion: 多个遮挡区域，模拟墨水污渍和纸张破损
    """
    damaged = image.copy()
    h, w = image.shape
    
    # 定义三级强度映射
    severity_params = {
        'light': {'noise_ratio': 0.08, 'erosion_kernel': 3, 'occlusion_count': 4},
        'medium': {'noise_ratio': 0.15, 'erosion_kernel': 4, 'occlusion_count': 6},
        'heavy': {'noise_ratio': 0.25, 'erosion_kernel': 5, 'occlusion_count': 9}
    }
    params = severity_params.get(severity, severity_params['medium'])

    if damage_type == "noise":
        # 🎯 椒盐噪声：用灰色調而非純黑，避免與筆畫混淆
        noise_ratio = params['noise_ratio']
        salt_pepper_mask = np.random.rand(h, w) < noise_ratio
        salt_mask = np.random.rand(h, w) > 0.5

        # 白點保持 255，「暗點」用中灰色 (120~180) 而非純黑
        damaged[salt_pepper_mask & salt_mask] = 255
        damaged[salt_pepper_mask & ~salt_mask] = np.random.randint(100, 170)

        # 高斯噪声加大
        gaussian_noise = np.random.normal(0, intensity * 30, image.shape).astype(np.int16)
        damaged = np.clip(damaged.astype(np.int16) + gaussian_noise, 0, 255).astype(np.uint8)

    elif damage_type == "erosion":
        # 🎯 形态学侵蚀：加大 kernel 使效果明顯可見
        kernel_size = params['erosion_kernel']
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        # 對黑色筆畫(0)在白色背景(255)上，dilate 使黑色區域縮小
        damaged = cv2.dilate(damaged, kernel, iterations=1)

    elif damage_type == "occlusion":
        # 🎯 半透明遮擋：用淺色方塊混合原圖，不用黑色
        num_occlusions = params['occlusion_count']

        for _ in range(num_occlusions):
            box_w = np.random.randint(int(w * 0.20), int(w * 0.45))
            box_h = np.random.randint(int(h * 0.20), int(h * 0.45))

            if h > box_h and w > box_w:
                y = np.random.randint(0, h - box_h)
                x = np.random.randint(0, w - box_w)

                # 遮擋顏色：淺灰到中灰 (150~220)，絕不用黑色
                occlusion_value = np.random.randint(150, 220)

                # 半透明混合 (alpha=0.5~0.7)，讓底下筆畫隱約可見
                alpha = np.random.uniform(0.5, 0.7)
                roi = damaged[y:y+box_h, x:x+box_w].astype(np.float32)
                blended = roi * (1 - alpha) + occlusion_value * alpha
                damaged[y:y+box_h, x:x+box_w] = blended.astype(np.uint8)

                # 邊緣高斯模糊使過渡更自然
                pad = 2
                y0, y1 = max(0, y - pad), min(h, y + box_h + pad)
                x0, x1 = max(0, x - pad), min(w, x + box_w + pad)
                roi_blur = damaged[y0:y1, x0:x1]
                if roi_blur.size > 0:
                    blurred = cv2.GaussianBlur(roi_blur, (5, 5), 0)
                    damaged[y0:y1, x0:x1] = blurred
    
    return damaged

def restore_with_magic(img_data, n_coeffs=40):
    """使用 FFT 低通濾波重建書法字：處理所有輪廓而非僅最大輪廓"""
    h, w = img_data.shape[:2]
    res_img = np.ones((h, w), dtype=np.uint8) * 255
    try:
        # 1. 降噪
        processed = cv2.medianBlur(img_data, 3)

        # 自適應閾值，對噪聲和遮擋更魯棒
        binary = cv2.adaptiveThreshold(
            processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # 形態學閉運算連接斷裂筆畫
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        # 2. 提取所有有效輪廓（過濾雜訊用面積閾值）
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        if not contours:
            print(f"  ⚠️ 未找到輪廓 (n_coeffs={n_coeffs})")
            return img_data

        # 過濾太小的雜訊輪廓（面積 < 圖片總面積的 0.5%）
        min_area = h * w * 0.005
        valid_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
        if not valid_contours:
            # 如果全被過濾掉，至少保留最大的
            valid_contours = [max(contours, key=cv2.contourArea)]

        total_pts = sum(len(c) for c in valid_contours)
        print(f"  找到 {len(valid_contours)} 個有效輪廓，共 {total_pts} 點 (n_coeffs={n_coeffs})")

        # 3. 把所有有效輪廓畫到遮罩上，再透過 SVG→FFT→重建
        temp_mask = np.ones((h, w), dtype=np.uint8) * 255
        cv2.drawContours(temp_mask, valid_contours, -1, 0, -1)

        temp_png = "./temp_restore_work.png"
        temp_svg = "./temp_restore_work.svg"
        cv2.imwrite(temp_png, temp_mask)
        bitmap_to_contour_svg(temp_png, temp_svg)

        # 4. FFT 重建所有筆畫
        recon_strokes, bbox = fft.get_reconstructed_points(temp_svg, n_coeffs=n_coeffs)

        if not recon_strokes:
            print(f"  ⚠️ FFT 重建失敗")
            return img_data

        # 5. 在 4x 高解析度畫布繪製再縮放回來（抗鋸齒）
        scale = 4
        hi_res = np.ones((h * scale, w * scale), dtype=np.uint8) * 255
        total_recon = 0
        for stroke_pts in recon_strokes:
            if len(stroke_pts) < 3:
                continue
            pts = np.array(stroke_pts, dtype=np.float32)
            pts[:, 0] = np.clip(pts[:, 0] * scale, 0, w * scale - 1)
            pts[:, 1] = np.clip(pts[:, 1] * scale, 0, h * scale - 1)
            pts = pts.reshape((-1, 1, 2)).astype(np.int32)
            cv2.fillPoly(hi_res, [pts], 0)
            total_recon += 1

        # 縮放回原始尺寸 — INTER_AREA 自然產生抗鋸齒灰階
        res_img = cv2.resize(hi_res, (w, h), interpolation=cv2.INTER_AREA)
        print(f"  ✓ FFT 重建 {total_recon} 個筆畫 (n_coeffs={n_coeffs})")
        return res_img

    except Exception as e:
        print(f"  修復中斷: {e}")
        return img_data

def create_comparison_report(img_path, damage_type="noise", intensity=0.3, severity="medium"):
    """產出 2x4 對照報告圖表"""
    IMG_SIZE = 128  # 提高解析度（原本 64 太小）

    original = cv2.imread(img_path, 0)
    if original is None: return
    original = cv2.resize(original, (IMG_SIZE, IMG_SIZE))
    damaged = add_damage(original, damage_type, intensity, severity)

    # 測試兩種係數級距：N=20 平滑但丟細節，N=80 保留更多筆畫特徵
    res_low = restore_with_magic(damaged, n_coeffs=20)
    res_high = restore_with_magic(damaged, n_coeffs=80)

    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    imgs = [original, damaged, res_low, res_high]

    damage_names = {
        "noise": "Noise",
        "erosion": "Erosion",
        "occlusion": "Occlusion"
    }
    damage_display = damage_names.get(damage_type, damage_type)

    titles = [
        "Original",
        f"Damaged ({damage_display})",
        "Restored (N=20)",
        "Restored (N=80)"
    ]

    # 上排：完整圖片
    for i in range(4):
        axes[0, i].imshow(imgs[i], cmap='gray', vmin=0, vmax=255)
        axes[0, i].set_title(titles[i], fontsize=13, fontweight='bold', pad=8)
        axes[0, i].axis('off')

    # 下排：中央局部放大（取中間 60% 區域）
    margin = IMG_SIZE // 5
    for i in range(4):
        zoom = imgs[i][margin:IMG_SIZE-margin, margin:IMG_SIZE-margin]
        axes[1, i].imshow(zoom, cmap='gray', vmin=0, vmax=255)
        axes[1, i].set_title("Detail View", fontsize=10, pad=5)
        axes[1, i].axis('off')

    plt.suptitle(f"Digital Restoration Analysis: {damage_type.upper()}",
                 fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = f"./output/restoration_{damage_type}_magic.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 報告已生成: {out_path}")