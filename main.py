import os
import glob
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import MaxNLocator
import cv2
from Preprocessing import clean_image
from SVG import bitmap_to_contour_svg
import fft

# Global matplotlib configuration to avoid font rendering issues
plt.rcParams['font.sans-serif'] = ['Arial', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['mathtext.fontset'] = 'dejavusans'  # Use DejaVu Sans for math text
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.usetex'] = False  # Disable LaTeX
plt.rcParams['mathtext.fallback'] = 'cm'  # Fallback to Computer Modern for math
plt.rcParams['pdf.fonttype'] = 42  # Use TrueType fonts

def annotate_perfect_report(img_path, styles):
    """專業影像後製：解決座標軸名稱與佈局對齊問題"""
    img = cv2.imread(img_path)
    if img is None: return
    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_DUPLEX

    # 1. 頂部標題區 (增加高度與白色底)
    cv2.rectangle(img, (0, 0), (w, 140), (255, 255, 255), -1)
    title = "Calligraphy Style Spectral Analysis"
    subtitle = "NTHU CS Project: Fourier Descriptor Fingerprint"
    
    # 計算置中位置
    (tw, _), _ = cv2.getTextSize(title, font, 1.4, 2)
    cv2.putText(img, title, ((w - tw) // 2, 65), font, 1.4, (44, 62, 80), 2, cv2.LINE_AA)
    (stw, _), _ = cv2.getTextSize(subtitle, font, 0.8, 1)
    cv2.putText(img, subtitle, ((w - stw) // 2, 110), font, 0.8, (127, 140, 141), 1, cv2.LINE_AA)

    # 2. X 軸標籤 (置中於圖表下方)
    x_label = "Frequency Index (0=Structure, >5=Stroke Details)"
    (xlw, _), _ = cv2.getTextSize(x_label, font, 0.9, 1)
    cv2.putText(img, x_label, ((w - xlw) // 2, h - 40), font, 0.9, (0, 0, 0), 2, cv2.LINE_AA)

    # 3. Y 軸標籤 (位於左側邊距，水平顯示)
    y_label_top = "Normalized"
    y_label_bot = "Magnitude"
    cv2.putText(img, y_label_top, (30, h // 2 - 20), font, 0.7, (50, 50, 50), 1, cv2.LINE_AA)
    cv2.putText(img, y_label_bot, (30, h // 2 + 20), font, 0.7, (50, 50, 50), 1, cv2.LINE_AA)

    # 4. 圖例區 (右上角加外框)
    legend_x = w - 380
    colors = [(255, 100, 100), (100, 200, 255), (100, 255, 100)] # BGR
    cv2.rectangle(img, (legend_x - 10, 160), (w - 40, 160 + len(styles)*55), (250, 250, 250), -1)
    cv2.rectangle(img, (legend_x - 10, 160), (w - 40, 160 + len(styles)*55), (200, 200, 200), 1)

    for i, name in enumerate(styles):
        y_pos = 210 + (i * 55)
        cv2.rectangle(img, (legend_x + 10, y_pos - 30), (legend_x + 50, y_pos), colors[i % 3], -1)
        cv2.putText(img, f"{name}", (legend_x + 65, y_pos - 5), font, 1.0, (0, 0, 0), 2, cv2.LINE_AA)

    cv2.imwrite(img_path, img)


def plot_style_results(styles_results, out_path, target_len=50):
    """產出雙面板風格對比圖：左=雷達圖，右=長條圖"""
    feature_labels = [
        'Low-freq\nEnergy', 'Mid-freq\nEnergy', 'High-freq\nEnergy',
        'Spectral\nCentroid', 'DC/Fund.\nRatio', 'Spectral\nSlope', 'HF Decay\nRate'
    ]
    n_features = len(feature_labels)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    names = sorted(styles_results.keys())

    fig, (ax_radar, ax_bar) = plt.subplots(1, 2, figsize=(18, 8),
                                            subplot_kw=dict(polar=True) if False else {},
                                            gridspec_kw={'width_ratios': [1, 1.2]})

    # --- 左面板：分組長條圖 ---
    # 先把各家特徵做 min-max 正規化以便視覺比較
    all_vecs = np.array([styles_results[n] for n in names])
    mins = all_vecs.min(axis=0)
    maxs = all_vecs.max(axis=0)
    ranges = maxs - mins
    ranges[ranges < 1e-10] = 1  # 避免除以零

    x = np.arange(n_features)
    bar_w = 0.8 / len(names)
    for i, name in enumerate(names):
        normed = (styles_results[name] - mins) / ranges
        ax_radar.bar(x + i * bar_w - 0.4 + bar_w / 2, normed, bar_w,
                     label=name, color=colors[i % len(colors)], alpha=0.85,
                     edgecolor='white', linewidth=0.8)
        # 在每根柱子上方標示原始值
        for j, (nv, rv) in enumerate(zip(normed, styles_results[name])):
            ax_radar.text(j + i * bar_w - 0.4 + bar_w / 2, nv + 0.02,
                         f'{rv:.3f}', ha='center', va='bottom', fontsize=7,
                         color=colors[i % len(colors)], fontweight='bold')

    ax_radar.set_xticks(x)
    ax_radar.set_xticklabels(feature_labels, fontsize=9)
    ax_radar.set_ylabel('Normalized Value', fontsize=11, fontweight='bold')
    ax_radar.set_title('Spectral Feature Comparison', fontsize=14, fontweight='bold', pad=15)
    ax_radar.legend(fontsize=10, title='Calligrapher', title_fontsize=11,
                    framealpha=0.9, edgecolor='#333')
    ax_radar.set_ylim(0, 1.35)
    ax_radar.grid(axis='y', alpha=0.3)
    for spine in ['top', 'right']:
        ax_radar.spines[spine].set_visible(False)

    # --- 右面板：原始值折線圖 (每個特徵一行) ---
    ax_bar.axis('off')
    cell_text = []
    for name in names:
        row = [f'{v:.4f}' for v in styles_results[name]]
        cell_text.append(row)

    short_labels = ['Low-E', 'Mid-E', 'High-E', 'Centroid', 'DC/Fund', 'Slope', 'Decay']
    table = ax_bar.table(cellText=cell_text, rowLabels=names,
                         colLabels=short_labels, loc='center',
                         cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.0)
    # 上色
    for i, name in enumerate(names):
        table[i + 1, -1].set_facecolor(colors[i % len(colors)] + '33')
        for j in range(n_features):
            table[i + 1, j].set_facecolor(colors[i % len(colors)] + '15')
    ax_bar.set_title('Raw Feature Values', fontsize=14, fontweight='bold', pad=20)

    fig.suptitle('Calligraphy Style Fourier Analysis', fontsize=20, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print(f"✓ 圖表已生成 (DPI=150): {out_path}")

def run_style_analysis(data_root="./data", output_dir="./output", max_samples=None):
    """
    執行完整的書法風格分析流程
    
    參數:
        data_root: 數據根目錄
        output_dir: 輸出目錄
        max_samples: 每位書法家的最大樣本數
                    - None: 使用所有樣本
                    - 50, 100: 指定數量
    
    流程:
        1. 批次處理每位書法家的字帖
        2. 提取傅立葉描述子頻譜
        3. 計算平均頻譜指紋
        4. 生成風格對比圖
        5. 計算相似度矩陣
        6. 產出詳細報告
    """
    if not os.path.exists(output_dir): 
        os.makedirs(output_dir)
    
    calligraphers = [d for d in os.listdir(data_root) 
                     if os.path.isdir(os.path.join(data_root, d))]
    TARGET_LEN = 50  # 使用前 50 個頻率分量，涵蓋更多筆畫細節差異
    
    # 決定樣本數
    if max_samples is None:
        sample_limit = float('inf')
        sample_note = "All available"
    else:
        sample_limit = max_samples
        sample_note = f"{max_samples} samples"
    
    print("\n" + "="*70)
    print(f" 書法風格傅立葉分析 (樣本: {sample_note})")
    print("="*70)
    
    styles_results = {}
    overall_stats = {}
    
    for name in sorted(calligraphers):
        print(f"\n 正在分析: {name}")
        img_paths = sorted(glob.glob(os.path.join(data_root, name, "*.[pj][np]g")))
        
        # 限制樣本數
        img_paths = img_paths[:int(sample_limit)]
        
        all_vecs = []
        success_count = 0
        fail_count = 0
        
        for idx, p in enumerate(img_paths, 1):
            try:
                # 預處理
                binary = clean_image(p)
                temp_binary = "./images/temp_clean.png"
                import cv2 as cv
                cv.imwrite(temp_binary, binary)
                
                # 轉 SVG
                temp_svg = "./images/temp_batch.svg"
                bitmap_to_contour_svg(temp_binary, temp_svg)
                
                # FFT 轉換
                fourier_data, _ = fft.fftProcess(temp_svg, n_coeffs=TARGET_LEN + 5)

                # 提取頻譜形狀特徵（比原始振幅更有區分力）
                if fourier_data:
                    stroke_features = []
                    for stroke_coeffs in fourier_data:
                        if len(stroke_coeffs) < TARGET_LEN:
                            continue
                        amps = np.array([max(1e-10, c[0]) for c in stroke_coeffs[:TARGET_LEN]])
                        total_e = np.sum(amps ** 2) + 1e-10

                        # 1) 各頻段能量比 (低/中/高)
                        low = np.sum(amps[:5] ** 2) / total_e
                        mid = np.sum(amps[5:15] ** 2) / total_e
                        high = np.sum(amps[15:] ** 2) / total_e

                        # 2) 頻譜重心 (centroid)
                        freqs = np.arange(TARGET_LEN, dtype=np.float64)
                        centroid = np.sum(freqs * amps) / (np.sum(amps) + 1e-10)

                        # 3) DC/基頻比
                        dc_fund_ratio = amps[0] / (amps[1] + 1e-10)

                        # 4) 頻譜斜率 (線性迴歸)
                        log_amps = np.log1p(amps)
                        slope = np.polyfit(freqs, log_amps, 1)[0]

                        # 5) 高頻衰減率
                        if amps[1] > 1e-10:
                            decay = np.mean(amps[10:20]) / amps[1]
                        else:
                            decay = 0.0

                        feat = [low, mid, high, centroid / TARGET_LEN,
                                dc_fund_ratio, abs(slope), decay]
                        stroke_features.append(feat)

                    if stroke_features:
                        avg_feature = np.mean(stroke_features, axis=0)
                        all_vecs.append(avg_feature)
                        success_count += 1
                    
                    # 進度指示
                    if idx % max(1, len(img_paths)//10) == 0:
                        print(f"   進度: {idx}/{len(img_paths)} ✓")
            
            except Exception as e:
                fail_count += 1
                if idx <= 3:  # 只列印前 3 個錯誤
                    print(f"   ⚠️  {os.path.basename(p)}: {type(e).__name__}")
        
        # 統計與平均
        if all_vecs:
            avg_vec = np.mean(np.vstack(all_vecs), axis=0)
            styles_results[name] = avg_vec
            
            overall_stats[name] = {
                'total_images': len(img_paths),
                'processed': success_count,
                'failed': fail_count,
                'success_rate': success_count / len(img_paths) * 100
            }
            
            print(f"   ✅ 已處理: {success_count}/{len(img_paths)} "
                  f"(成功率: {overall_stats[name]['success_rate']:.1f}%)")
        else:
            print(f"   ❌ {name}: 沒有有效樣本！")
    
    if not styles_results:
        print("❌ 無法生成結果，請檢查數據！")
        return
    
    # ===== 任務 2: 產出風格對比圖 =====
    print("\n 生成風格對比圖...")
    report_path = os.path.join(output_dir, "style_analysis_report.png")
    plot_style_results(styles_results, report_path, TARGET_LEN)
    
    # ===== 任務 3: 計算相似度矩陣 =====
    print(" 計算相似度矩陣...")
    try:
        from modules.similarity_analyzer import compute_similarity_matrix, plot_similarity_heatmap, print_similarity_report
        
        sim_df, sim_scores = plot_similarity_heatmap(styles_results, 
                                                      os.path.join(output_dir, "similarity_matrix.png"))
        print_similarity_report(sim_df, sim_scores)
    except ImportError:
        print("   ⚠️  similarity_analyzer 模組未找到，跳過相似度計算")
    
    # ===== 產出統計報告 =====
    print("\n 處理統計:")
    print("-" * 70)
    for name in sorted(overall_stats.keys()):
        stats = overall_stats[name]
        print(f"  {name:20s}: {stats['processed']:3d}/{stats['total_images']:3d} "
              f"({stats['success_rate']:5.1f}%)")
    print("-" * 70)
    
    print(f"\n 分析完成！")
    print(f"   - 報表: {report_path}")
    print(f"   - 相似度熱圖: {os.path.join(output_dir, 'similarity_matrix.png')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    # 一鍵全部：風格分析 + 修復演示
    import sys
    
    if len(sys.argv) > 1:
        try:
            max_samples = int(sys.argv[1])
        except ValueError:
            print(f"❌ 無效參數: {sys.argv[1]}")
            print("用法: py main.py [樣本數]")
            print("例如: py main.py 100")
            sys.exit(1)
    else:
        # 預設: 30個樣本（快速測試）
        max_samples = 30
    
    # ===== 階段 1: 風格分析 =====
    print("           開始一鍵全部執行流程")
    run_style_analysis(max_samples=max_samples)
    
    # ===== 階段 2: 修復演示 =====
    print("\n" + "="*70)
    print(" 開始執行修復壓力測試...")
    print("="*70 + "\n")
    
    try:
        from modules.restoration_demo import create_comparison_report
        
        # 找測試圖片
        test_img = None
        for calligrapher in ["Yan_Zhenqing", "Liu_Gongquan", "Ou_Yangxun"]:
            folder = f"./data/{calligrapher}"
            if os.path.exists(folder):
                images = sorted([f for f in os.listdir(folder) if f.endswith(('.png', '.jpg'))])
                if images:
                    test_img = os.path.join(folder, images[0])
                    break
        
        if test_img:
            print(f"✓ 使用測試圖片: {test_img}\n")
            
            # 執行三種損壞類型的測試
            print(" 執行修復示範測試 (3 種損壞模式)...")
            print("-" * 70)
            
            create_comparison_report(test_img, damage_type="noise", intensity=0.2)
            create_comparison_report(test_img, damage_type="erosion", intensity=0.3)
            create_comparison_report(test_img, damage_type="occlusion", intensity=0.25)
            
            print("-" * 70)
            print("\n✨ 修復測試完成！\n")
        else:
            print("⚠️  未找到測試圖片，跳過修復演示")
    
    except ImportError as e:
        print(f"⚠️  無法載入修復模組: {e}")
    except Exception as e:
        print(f"⚠️  修復演示執行出錯: {e}")
    
    # ===== 完成總結 =====
    print("="*70)
    print("✅ 一鍵全部執行完成！")
    print("="*70)
    print("\n📊 實際生成的報告文件（請至 ./output/ 查看）：")
    print(f"   ./output/style_analysis_report.png        (風格對比圖)")
    print(f"   ./output/similarity_matrix.png             (相似度熱圖)")
    print(f"   ./output/restoration_noise_magic.png       (抗噪實心測試)") # 修正這裡   
    print(f"   ./output/restoration_erosion_magic.png     (抗侵蝕實心測試)") # 修正這裡
    print(f"   ./output/restoration_occlusion_magic.png   (抗遮蔽實心測試)") # 修正這裡
    print("="*70)