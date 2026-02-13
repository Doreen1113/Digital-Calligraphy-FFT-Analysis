import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from Preprocessing import clean_image
from SVG import bitmap_to_contour_svg
import fft

# 解決字體顯示問題
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass

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
    """【核心修正】正確對接 FFT 回傳值並實現實心修復"""
    h, w = 64, 64
    res_img = np.ones((h, w), dtype=np.uint8) * 255
    try:
        # 1. 適度降噪（避免過度處理導致特徵丟失）
        processed = cv2.medianBlur(img_data, 3)  # 降低濾波強度從5改為3
        
        # 使用自適應閾值處理，對噪聲和遮擋更魯棒
        binary = cv2.adaptiveThreshold(
            processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # 輕微的形態學閉運算連接斷裂筆畫
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        # 2. 提取最大輪廓，避免修復到背景雜訊
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print(f"⚠️ 未找到輪廓，返回原圖 (n_coeffs={n_coeffs})")
            return img_data
        
        main_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(main_contour)
        print(f"🔍 找到輪廓，面積={contour_area:.0f} (n_coeffs={n_coeffs})")
        
        temp_mask = np.ones((h, w), dtype=np.uint8) * 255
        cv2.drawContours(temp_mask, [main_contour], -1, 0, -1)
        
        # 3. 轉向量並執行 FFT
        cv2.imwrite("temp_restore_final.png", temp_mask)
        bitmap_to_contour_svg("temp_restore_final.png", "temp_restore_final.svg")
        
        # ✨ 關鍵修正：使用 get_reconstructed_points 獲取重建座標
        recon_strokes, bbox = fft.get_reconstructed_points("temp_restore_final.svg", n_coeffs=n_coeffs)
        
        if recon_strokes and len(recon_strokes) > 0:
            # 取第一個筆劃（主要輪廓）
            recon_points = recon_strokes[0] if len(recon_strokes) > 0 else []
            
            if len(recon_points) > 2:  # 至少需要3個點才能形成多邊形
                print(f"✓ FFT重建 {len(recon_points)} 個點 (n_coeffs={n_coeffs})")
                
                # 轉換為 OpenCV 格式
                pts = np.array(recon_points, dtype=np.float32)
                
                # 如果SVG座標系統和圖像不同，需要調整（通常SVG原點在左上）
                # 座標已經在正確的範圍內，直接使用
                pts = pts.reshape((-1, 1, 2)).astype(np.int32)
            
# 轉換為 OpenCV 格式
                pts = np.array(recon_points, dtype=np.float32)
                
                # 如果SVG座標系統和圖像不同，需要調整（通常SVG原點在左上）
                # 座標已經在正確的範圍內，直接使用
                pts = pts.reshape((-1, 1, 2)).astype(np.int32)
                
                # 確保座標在合理範圍內
                x_coords = pts[:, 0, 0]
                y_coords = pts[:, 0, 1]
                
                # 裁剪到有效範圍
                pts[:, 0, 0] = np.clip(x_coords, 0, w-1)
                pts[:, 0, 1] = np.clip(y_coords, 0, h-1)
                
                # 填充重建的輪廓
                cv2.fillPoly(res_img, [pts], 0)  # 0 代表黑色實心填充
                return res_img
            else:
                print(f"⚠️ FFT重建點數不足 ({len(recon_points)} 點)，返回原圖")
                return img_data
            
        return img_data
    except Exception as e:
        print(f"修復中斷: {e}")
        return img_data

def create_comparison_report(img_path, damage_type="noise", intensity=0.3, severity="medium"):
    """產出 2x4 對照報告圖表
    
    Args:
        img_path: 原始圖像路徑
        damage_type: 破壞類型
        intensity: 破壞強度
        severity: 破壞等級 (light/medium/heavy)
    """
    original = cv2.imread(img_path, 0)
    if original is None: return
    original = cv2.resize(original, (64, 64))
    damaged = add_damage(original, damage_type, intensity, severity)
    
    # 測試係數級距 [50, 100]
    res_low = restore_with_magic(damaged, n_coeffs=50)
    res_high = restore_with_magic(damaged, n_coeffs=100)
    
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    imgs = [original, damaged, res_low, res_high]
    
    # 改进的标题，包含破坏类型和等级信息
    damage_names = {
        "noise": "噪声 (noise)",
        "erosion": "侵蚀 (erosion)", 
        "occlusion": "遮挡 (occlusion)"
    }
    damage_display = damage_names.get(damage_type, damage_type)
    
    titles = [
        "Original", 
        f"Damaged ({damage_display})", 
        "Restored (N=50)", 
        "Restored (N=100)"
    ]
    
    for i in range(4):
        axes[0, i].imshow(imgs[i], cmap='gray')
        axes[0, i].set_title(titles[i], fontsize=13, fontweight='bold', pad=8)
        axes[0, i].axis('off')
        
    for i in range(4):
        zoom = imgs[i][17:47, 17:47] # 局部放大
        axes[1, i].imshow(zoom, cmap='gray')
        axes[1, i].set_title("Detail View", fontsize=10, pad=5)
        axes[1, i].axis('off')

    plt.suptitle(f"Digital Restoration Analysis: {damage_type.upper()}", 
                 fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"./output/restoration_{damage_type}_magic.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 報告已生成: ./output/restoration_{damage_type}_magic.png")