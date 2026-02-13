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
        'light': {'noise_ratio': 0.05, 'erosion_kernel': 2, 'occlusion_count': 2},
        'medium': {'noise_ratio': 0.10, 'erosion_kernel': 3, 'occlusion_count': 3},
        'heavy': {'noise_ratio': 0.20, 'erosion_kernel': 4, 'occlusion_count': 5}
    }
    params = severity_params.get(severity, severity_params['medium'])
    
    if damage_type == "noise":
        # 🎯 椒盐噪声：密密麻麻的黑白像素点
        noise_ratio = params['noise_ratio'] * intensity
        salt_pepper_mask = np.random.rand(h, w) < noise_ratio
        salt_mask = np.random.rand(h, w) > 0.5  # 50% 白点, 50% 黑点
        
        damaged[salt_pepper_mask & salt_mask] = 255  # 盐噪声 (白点)
        damaged[salt_pepper_mask & ~salt_mask] = 0   # 椒噪声 (黑点)
        
        # 混合轻微高斯噪声增加真实感
        gaussian_noise = np.random.normal(0, intensity * 15, image.shape).astype(np.int16)
        damaged = np.clip(damaged.astype(np.int16) + gaussian_noise, 0, 255).astype(np.uint8)
        
    elif damage_type == "erosion":
        # 🎯 形态学侵蚀：笔画变细，转折处轻微断裂
        kernel_size = params['erosion_kernel']
        # 使用椭圆形kernel使效果更自然
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        # 对于黑色笔画(0)在白色背景(255)上，使用dilate使黑色区域变细
        damaged = cv2.dilate(damaged, kernel, iterations=1)
        
    elif damage_type == "occlusion":
        # 🎯 多区域遮挡：模拟墨水污渍、印章、纸张破损
        num_occlusions = params['occlusion_count']
        
        for _ in range(num_occlusions):
            # 隨機大小：10×10 到 25×25 像素（更明顯的遮擋）
            box_w = np.random.randint(int(w * 0.15), int(w * 0.40))
            box_h = np.random.randint(int(h * 0.15), int(h * 0.40))
            
            # 随机位置
            if h > box_h and w > box_w:
                y = np.random.randint(0, h - box_h)
                x = np.random.randint(0, w - box_w)
                
                # 随机遮挡类型：浅灰污渍 (70%) 或深色墨水 (30%)
                if np.random.rand() > 0.3:
                    occlusion_value = np.random.randint(180, 230)  # 浅灰污渍
                else:
                    occlusion_value = np.random.randint(0, 50)     # 深色墨水
                
                # 创建遮挡区域
                damaged[y:y+box_h, x:x+box_w] = occlusion_value
                
                # 添加边缘渐变使遮挡更自然
                roi = damaged[max(0,y-1):min(h,y+box_h+1), max(0,x-1):min(w,x+box_w+1)]
                if roi.size > 0:
                    blurred = cv2.GaussianBlur(roi, (3, 3), 0)
                    damaged[max(0,y-1):min(h,y+box_h+1), max(0,x-1):min(w,x+box_w+1)] = blurred
    
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

        # 5. 將所有重建的筆畫畫回圖片
        total_recon = 0
        for stroke_pts in recon_strokes:
            if len(stroke_pts) < 3:
                continue
            pts = np.array(stroke_pts, dtype=np.float32)
            pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)
            pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)
            pts = pts.reshape((-1, 1, 2)).astype(np.int32)
            cv2.fillPoly(res_img, [pts], 0)
            total_recon += 1

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

    # 測試兩種係數級距
    res_low = restore_with_magic(damaged, n_coeffs=50)
    res_high = restore_with_magic(damaged, n_coeffs=100)

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
        "Restored (N=50)",
        "Restored (N=100)"
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