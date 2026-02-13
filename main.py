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


def plot_style_results(styles_results, out_path, target_len=20):
    """Create a professional, publication-ready plot with optimized visual hierarchy.
    
    Improvements:
    - Better color palette (professional and distinguishable)
    - Enhanced typography and layout
    - Improved grid and axis styling
    - Linear scale for clearer data visualization
    - Optimized line and marker sizes
    - Better legend positioning and styling
    - Professional title with subtitle
    """
    # Register matplotlib's bundled DejaVu Sans font explicitly to avoid findfont issues
    try:
        data_path = matplotlib.get_data_path()
        dejavu_path = os.path.join(data_path, 'fonts', 'ttf', 'DejaVuSans.ttf')
        if os.path.exists(dejavu_path):
            fm.fontManager.addfont(dejavu_path)
            fp = fm.FontProperties(fname=dejavu_path)
            matplotlib.rcParams['font.family'] = fp.get_name()
    except Exception:
        pass

    # Figure setup with better proportions
    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111)

    # Professional color palette (optimized for visibility and aesthetics)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    line_styles = ['-', '-', '-', '-', '-', '-']
    
    # Plot each style with optimized styling
    names = sorted(styles_results.keys())
    for i, name in enumerate(names):
        vec = np.asarray(styles_results[name])[:target_len]
        vec = np.clip(vec, 1e-8, None)
        x = np.arange(len(vec))
        
        ax.plot(x, vec, 
                label=name, 
                linewidth=2.5,
                marker='o', 
                markersize=7,
                markerfacecolor=colors[i % len(colors)],
                markeredgewidth=1.5,
                markeredgecolor='white',
                color=colors[i % len(colors)],
                linestyle=line_styles[i % len(line_styles)],
                alpha=0.85,
                zorder=3)

    # Enhanced title and labels
    fig.suptitle('Calligraphy Style Spectral Analysis', 
                 fontsize=18, fontweight='bold', y=0.98)
    # ax.text(0.5, 0.94, 'NTHU CS Project: Fourier Descriptor Fingerprint', 
    #         transform=fig.transFigure, ha='center', fontsize=11, 
    #         style='italic', color='#555555')

    # Improved axis labels
    ax.set_xlabel('Frequency Index (0=Structure, >5=Stroke Details)', 
                  fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Normalized Magnitude', 
                  fontsize=12, fontweight='bold', labelpad=10)

    # Set proper bounds and ticks
    ax.set_xlim(-0.5, target_len - 0.5)
    ax.set_xbound(0, target_len - 1)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    
    # Use linear scale for better data visibility (no log scale)
    y_max = max([np.max(np.asarray(v)[:target_len]) for v in styles_results.values()]) * 1.1
    ax.set_ylim(0, y_max * 1.15)
    
    # Enhanced grid styling - primary and secondary
    ax.grid(True, which='major', linestyle='-', linewidth=1.0, alpha=0.3, zorder=0, color='#cccccc')
    ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.15, zorder=0, color='#e0e0e0')
    ax.minorticks_on()

    # Professional axis styling
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_visible(True)
        ax.spines[spine].set_linewidth(1.5)
        ax.spines[spine].set_color('#333333')

    # Enhanced tick styling
    ax.tick_params(axis='both', which='major', labelsize=10, width=1.5, length=6, colors='#333333')
    ax.tick_params(axis='both', which='minor', labelsize=9, width=1.0, length=3, colors='#666666')

    # Professional legend with enhanced styling
    legend = ax.legend(frameon=True, loc='upper right', fontsize=11, 
                       framealpha=0.95, edgecolor='#333333', fancybox=True, 
                       shadow=True, title='Calligrapher')
    legend.get_title().set_fontweight('bold')
    legend.get_title().set_fontsize(12)
    legend.get_frame().set_linewidth(1.5)
    legend.get_frame().set_facecolor('#ffffff')

    # Adjust layout to prevent label cutoff
    plt.subplots_adjust(left=0.10, right=0.95, top=0.92, bottom=0.12)
    
    # Save with high quality
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"✓ 高品質圖表已生成: {out_path}")

def run_style_analysis(data_root="./data", output_dir="./output"):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    calligraphers = [d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))]
    TARGET_LEN = 20  # 使用前 20 個頻率分量做為分析基準

    styles_results = {}
    for name in calligraphers:
        print(f"--- 正在分析 {name} ---")
        img_paths = glob.glob(os.path.join(data_root, name, "*.[pj][np]g"))
        all_vecs = []
        for p in img_paths[:30]:
            try:
                binary = clean_image(p)
                temp_binary = "./images/temp_clean.png"
                import cv2 as cv
                cv.imwrite(temp_binary, binary)
                temp_svg = "./images/temp_batch.svg"
                bitmap_to_contour_svg(temp_binary, temp_svg)
                fourier_data, _ = fft.fftProcess(temp_svg, n_coeffs=TARGET_LEN + 5)

                if fourier_data and len(fourier_data[0]) >= TARGET_LEN:
                    amplitudes = np.array([max(1e-6, c[0]) for c in fourier_data[0][:TARGET_LEN]])
                    amplitudes = amplitudes / amplitudes[0]
                    all_vecs.append(amplitudes)
            except Exception:
                continue

        if all_vecs:
            avg_vec = np.mean(np.vstack(all_vecs), axis=0)
            styles_results[name] = avg_vec

    # plot results using a clean helper
    report_path = os.path.join(output_dir, "style_analysis_report.png")
    plot_style_results(styles_results, report_path, TARGET_LEN)
    print(f"🎉 成功！報表已產出：{report_path}")

if __name__ == "__main__":
    run_style_analysis()