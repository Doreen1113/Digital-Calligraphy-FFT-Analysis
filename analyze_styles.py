"""Execute FFT style analysis for 4 calligraphers"""
import os
import sys
import glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cv2

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.core.preprocessing import clean_image
from core.SVG import bitmap_to_contour_svg
from core import fft
from src.utils import get_config, FontDataLoader

# Matplotlib configuration for Chinese characters
import matplotlib.font_manager as fm
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'sans-serif']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.usetex'] = False

# Force matplotlib to use Chinese fonts
try:
    import matplotlib
    matplotlib.font_manager._rebuild()
except:
    pass


def plot_style_results(styles_results, out_path, target_len=50):
    """Generate style comparison chart: bar chart + value table"""
    feature_labels = [
        'Low-freq\nEnergy', 'Mid-freq\nEnergy', 'High-freq\nEnergy',
        'Spectral\nCentroid', 'DC/Fund.\nRatio', 'Spectral\nSlope', 'HF Decay\nRate'
    ]
    n_features = len(feature_labels)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    names = sorted(styles_results.keys())

    fig, (ax_bar, ax_table) = plt.subplots(1, 2, figsize=(18, 8),
                                            gridspec_kw={'width_ratios': [1, 1.2]})

    # Left panel: Grouped bar chart
    all_vecs = np.array([styles_results[n] for n in names])
    mins = all_vecs.min(axis=0)
    maxs = all_vecs.max(axis=0)
    ranges = maxs - mins
    ranges[ranges < 1e-10] = 1

    x = np.arange(n_features)
    bar_w = 0.8 / len(names)
    for i, name in enumerate(names):
        normed = (styles_results[name] - mins) / ranges
        ax_bar.bar(x + i * bar_w - 0.4 + bar_w / 2, normed, bar_w,
                   label=name, color=colors[i % len(colors)], alpha=0.85,
                   edgecolor='white', linewidth=0.8)
        for j, (nv, rv) in enumerate(zip(normed, styles_results[name])):
            ax_bar.text(j + i * bar_w - 0.4 + bar_w / 2, nv + 0.02,
                       f'{rv:.3f}', ha='center', va='bottom', fontsize=7,
                       color=colors[i % len(colors)], fontweight='bold')

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(feature_labels, fontsize=9)
    ax_bar.set_ylabel('Normalized Value', fontsize=11, fontweight='bold')
    ax_bar.set_title('Spectral Feature Comparison', fontsize=14, fontweight='bold', pad=15)
    ax_bar.legend(fontsize=10, title='Calligrapher', title_fontsize=11,
                  framealpha=0.9, edgecolor='#333')
    ax_bar.set_ylim(0, 1.35)
    ax_bar.grid(axis='y', alpha=0.3)
    for spine in ['top', 'right']:
        ax_bar.spines[spine].set_visible(False)

    # Right panel: Value table
    ax_table.axis('off')
    cell_text = []
    for name in names:
        row = [f'{v:.4f}' for v in styles_results[name]]
        cell_text.append(row)

    short_labels = ['Low-E', 'Mid-E', 'High-E', 'Centroid', 'DC/Fund', 'Slope', 'Decay']
    table = ax_table.table(cellText=cell_text, rowLabels=names,
                           colLabels=short_labels, loc='center',
                           cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.0)
    for i, name in enumerate(names):
        table[i + 1, -1].set_facecolor(colors[i % len(colors)] + '33')
        for j in range(n_features):
            table[i + 1, j].set_facecolor(colors[i % len(colors)] + '15')
    ax_table.set_title('Raw Feature Values', fontsize=14, fontweight='bold', pad=20)

    fig.suptitle('Calligraphy Style Fourier Analysis', fontsize=20, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] Chart saved (DPI=150): {out_path}")


def run_style_analysis(max_samples=None):
    """Execute complete calligraphy style analysis workflow"""
    config = get_config()
    loader = FontDataLoader()

    output_dir = config.get_output_dir('base_dir')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    calligraphers = loader.get_calligrapher_list(use_display_name=False)  # 使用英文名稱做內部處理
    calligraphers_display = {cal['name']: cal['display_name'] for cal in loader.calligraphers}
    TARGET_LEN = config.get('fft', 'target_length', default=50)

    if max_samples is None:
        sample_limit = float('inf')
        sample_note = "All available"
    else:
        sample_limit = max_samples
        sample_note = f"{max_samples} samples"

    print("\n" + "="*70)
    print(f" Calligraphy Style Fourier Analysis (Samples: {sample_note})")
    print("="*70)

    styles_results = {}
    overall_stats = {}

    for name in sorted(calligraphers):
        display_name = calligraphers_display[name]
        print(f"\n 分析: {display_name}")

        info = loader.get_calligrapher_info(name)
        img_dir = info['image_dir']
        img_paths = sorted(glob.glob(os.path.join(img_dir, "*.[pj][np]g")))

        img_paths = img_paths[:int(sample_limit)]

        all_vecs = []
        success_count = 0
        fail_count = 0

        for idx, p in enumerate(img_paths, 1):
            try:
                # Preprocessing
                binary = clean_image(p)
                temp_binary = "./output/temp/temp_clean.png"
                os.makedirs(os.path.dirname(temp_binary), exist_ok=True)
                cv2.imwrite(temp_binary, binary)

                # Convert to SVG
                temp_svg = "./output/temp/temp_batch.svg"
                bitmap_to_contour_svg(temp_binary, temp_svg)

                # FFT transform
                fourier_data, _ = fft.fftProcess(temp_svg, n_coeffs=TARGET_LEN + 5)

                if fourier_data:
                    stroke_features = []
                    for stroke_coeffs in fourier_data:
                        if len(stroke_coeffs) < TARGET_LEN:
                            continue
                        amps = np.array([max(1e-10, c[0]) for c in stroke_coeffs[:TARGET_LEN]])
                        total_e = np.sum(amps ** 2) + 1e-10

                        # Frequency band energy
                        low = np.sum(amps[:5] ** 2) / total_e
                        mid = np.sum(amps[5:15] ** 2) / total_e
                        high = np.sum(amps[15:] ** 2) / total_e

                        # Spectral centroid
                        freqs = np.arange(TARGET_LEN, dtype=np.float64)
                        centroid = np.sum(freqs * amps) / (np.sum(amps) + 1e-10)

                        # DC/Fundamental ratio
                        dc_fund_ratio = amps[0] / (amps[1] + 1e-10)

                        # Spectral slope
                        log_amps = np.log1p(amps)
                        slope = np.polyfit(freqs, log_amps, 1)[0]

                        # High frequency decay rate
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

                    if idx % max(1, len(img_paths)//10) == 0:
                        print(f"   Progress: {idx}/{len(img_paths)}")

            except Exception as e:
                fail_count += 1
                if idx <= 3:
                    print(f"   [Warning] {os.path.basename(p)}: {type(e).__name__}")

        if all_vecs:
            avg_vec = np.mean(np.vstack(all_vecs), axis=0)
            styles_results[display_name] = avg_vec  # 使用中文顯示名稱

            overall_stats[display_name] = {
                'total_images': len(img_paths),
                'processed': success_count,
                'failed': fail_count,
                'success_rate': success_count / len(img_paths) * 100
            }

            print(f"   [OK] 已處理: {success_count}/{len(img_paths)} "
                  f"(成功率: {overall_stats[display_name]['success_rate']:.1f}%)")
        else:
            print(f"   [Error] {display_name}: 沒有有效樣本！")

    if not styles_results:
        print("[Error] 無法產生結果！")
        return

    # Generate style comparison chart
    print("\n 產生風格比較圖表...")
    report_path = os.path.join(output_dir, "style_analysis_report.png")
    plot_style_results(styles_results, report_path, TARGET_LEN)

    # Compute similarity matrix
    print(" 計算相似度矩陣...")
    try:
        from src.analysis.similarity_analyzer import plot_similarity_heatmap, print_similarity_report

        sim_df, sim_scores = plot_similarity_heatmap(styles_results,
                                                      os.path.join(output_dir, "similarity_matrix.png"))
        print_similarity_report(sim_df, sim_scores)
    except ImportError:
        print("   [Warning] similarity_analyzer module not found, skipping")

    # Print processing statistics
    print("\n 處理統計:")
    print("-" * 70)
    max_name_len = max(len(name) for name in overall_stats.keys())
    for name in sorted(overall_stats.keys()):
        stats = overall_stats[name]
        print(f"  {name:<{max_name_len}s} : {stats['processed']:3d}/{stats['total_images']:3d} "
              f"({stats['success_rate']:5.1f}%)")
    print("-" * 70)

    print(f"\n 分析完成！")
    print(f"   - 報告: {report_path}")
    print(f"   - 相似度熱力圖: {os.path.join(output_dir, 'similarity_matrix.png')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        try:
            max_samples = int(sys.argv[1])
        except ValueError:
            print(f"[Error] 無效參數: {sys.argv[1]}")
            print("使用方式: py analyze_styles.py [樣本數]")
            print("範例: py analyze_styles.py 100")
            sys.exit(1)
    else:
        max_samples = 30

    print("           開始 FFT 風格分析")
    run_style_analysis(max_samples=max_samples)

    print("\n" + "="*70)
    print("[OK] 分析完成！")
    print("="*70)
    print("\n已產生報告:")
    print(f"   ./output/style_analysis_report.png        (風格比較)")
    print(f"   ./output/similarity_matrix.png             (相似度熱力圖)")
    print("="*70)
