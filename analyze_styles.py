"""Execute FFT style analysis for 4 calligraphers"""
import os
import sys
import glob
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cv2

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.core.preprocessing import clean_image
from src.core.svg import bitmap_to_contour_svg
from src.core import fft
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


def _compute_significance(vecs_by_display, cal_names, n_features):
    """
    對每個特徵做單因子 ANOVA（書法家 = 組別），取得 p 值跟效果量 eta^2。

    用逐張圖片的原始特徵值（而非先平均掉的彙總值）做檢定，才能正確反映
    樣本數對統計檢定力的影響——單純比較「全距 vs 標準差」的土法煉鋼方式，
    完全沒考慮樣本數多寡，樣本數夠大時再小的差異也會被誤判為雜訊。

    eta^2（效果量）：書法家身份能解釋的變異比例。依 Cohen 慣例，
    0.01=小、0.06=中、0.14=大——即使 p 值顯著，若 eta^2 很小，
    代表這個特徵對「風格辨識」的實際貢獻有限，只是統計上測得到而已。
    """
    from scipy import stats as scipy_stats

    anova_p = []
    eta_squared = []
    for i in range(n_features):
        groups = [np.array(vecs_by_display[n])[:, i] for n in cal_names]
        try:
            _, p = scipy_stats.f_oneway(*groups)
        except Exception:
            p = 1.0

        all_vals = np.concatenate(groups)
        grand_mean = np.mean(all_vals)
        ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups)
        ss_total = np.sum((all_vals - grand_mean) ** 2)
        eta_sq = ss_between / ss_total if ss_total > 0 else 0.0

        anova_p.append(float(p))
        eta_squared.append(float(eta_sq))

    return anova_p, eta_squared


def _save_analysis_json(styles_results, config, styles_std=None, vecs_by_display=None,
                         sample_sizes=None, common_char_count=0):
    """
    將 FFT 分析結果存為 JSON，供 Web 互動圖表使用

    輸出:
      data/index/style_features.json   → 雷達圖數據（原始值 + 正規化值 + 標準差 + 統計檢定）
      data/index/similarity_matrix.json → 相似度矩陣

    styles_std: 每位書法家每個特徵的標準差（同一人不同字之間的自然變化程度）。
    vecs_by_display: 每位書法家逐張圖片的原始特徵向量，用來做真正的 ANOVA 統計
    檢定（見 _compute_significance），比單純比較全距與標準差更嚴謹。
    """
    import json

    index_dir = os.path.join(os.path.dirname(__file__), "data", "index")
    os.makedirs(index_dir, exist_ok=True)

    # ---- 特徵順序 & 標籤 ----
    feature_order = ['low_freq', 'mid_freq', 'high_freq', 'centroid',
                     'dc_ratio', 'slope', 'hf_decay']
    # 面向觀眾的易懂中文標籤
    feature_labels = [
        '結構穩定度', '筆畫變化度', '細節豐富度', '細節vs結構',
        '字形完整度', '細節保留度', '收筆乾淨度'
    ]

    cal_names = sorted(styles_results.keys())
    raw_matrix = np.array([styles_results[n] for n in cal_names])

    # ---- Min-Max 正規化 (0-1) ----
    min_vals = raw_matrix.min(axis=0)
    max_vals = raw_matrix.max(axis=0)
    ranges = max_vals - min_vals
    ranges[ranges < 1e-10] = 1

    normalized = {}
    raw_data = {}
    std_data = {}
    for name in cal_names:
        vec = styles_results[name]
        norm_vec = (vec - min_vals) / ranges
        normalized[name] = [round(float(v), 4) for v in norm_vec]
        raw_data[name] = [round(float(v), 6) for v in vec]
        if styles_std and name in styles_std:
            std_data[name] = [round(float(v), 6) for v in styles_std[name]]

    anova_p = []
    eta_squared = []
    if vecs_by_display:
        anova_p, eta_squared = _compute_significance(vecs_by_display, cal_names, len(feature_order))

    style_json = {
        "calligraphers": cal_names,
        "labels": feature_labels,
        "feature_keys": feature_order,
        "data": normalized,
        "raw_data": raw_data,
        "std_data": std_data,
        "anova_p": [round(p, 6) for p in anova_p],
        "eta_squared": [round(e, 4) for e in eta_squared],
        "sample_sizes": sample_sizes or {},
        "common_char_count": common_char_count,
    }

    style_path = os.path.join(index_dir, "style_features.json")
    with open(style_path, 'w', encoding='utf-8') as f:
        json.dump(style_json, f, ensure_ascii=False, indent=2)
    print(f"   [OK] 風格特徵 JSON: {style_path}")

    # ---- 相似度矩陣 ----
    try:
        from src.analysis.similarity_analyzer import compute_similarity_matrix
        sim_df, sim_scores = compute_similarity_matrix(styles_results)

        sim_json = {
            "calligraphers": list(sim_df.index),
            "matrix": [[round(float(v), 4) for v in row]
                        for row in sim_df.values],
        }

        sim_path = os.path.join(index_dir, "similarity_matrix.json")
        with open(sim_path, 'w', encoding='utf-8') as f:
            json.dump(sim_json, f, ensure_ascii=False, indent=2)
        print(f"   [OK] 相似度矩陣 JSON: {sim_path}")
    except Exception as e:
        print(f"   [Warning] 相似度 JSON 儲存失敗: {e}")


def _load_common_char_paths(root_dir):
    """
    讀取 character_index.json 裡「所有書法家都寫過的共同字」清單，
    回傳 {internal_name: [image_path, ...]}，只包含共同字的圖片路徑。

    用意：現行做法把每位書法家寫過的「所有字」（字數、複雜度都不同）混在
    一起平均，會把「字本身筆畫多寡造成的差異」跟「書法家個人風格差異」
    混淆在一起。只用共同字，可以控制掉字本身複雜度的干擾，讓比較更公平。
    """
    idx_path = os.path.join(root_dir, "data", "index", "character_index.json")
    with open(idx_path, encoding="utf-8") as f:
        idx = json.load(f)

    common_chars = idx["common_characters"]
    char_map = idx["character_map"]
    calligraphers = idx["calligraphers"]

    paths_by_cal = {cal: [] for cal in calligraphers}
    for ch in common_chars:
        entries = char_map.get(ch, {})
        for cal in calligraphers:
            for e in entries.get(cal, []):
                img_path = os.path.join(root_dir, "Fonts", "my_fonts", e["font_id"], e["filename"])
                if os.path.exists(img_path):
                    paths_by_cal[cal].append(img_path)

    return paths_by_cal, common_chars


def run_style_analysis(max_samples=None, use_common_chars_only=True):
    """Execute complete calligraphy style analysis workflow"""
    config = get_config()
    loader = FontDataLoader()

    output_dir = config.get_output_dir('base_dir')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    calligraphers = loader.get_calligrapher_list(use_display_name=False)  # 使用英文名稱做內部處理
    calligraphers_display = {cal['name']: cal['display_name'] for cal in loader.calligraphers}
    TARGET_LEN = config.get('fft', 'target_length', default=50)

    common_char_paths = {}
    common_chars = []
    if use_common_chars_only:
        common_char_paths, common_chars = _load_common_char_paths(os.path.dirname(__file__))

    if max_samples is None:
        sample_limit = float('inf')
        sample_note = "All available"
    else:
        sample_limit = max_samples
        sample_note = f"{max_samples} samples"

    print("\n" + "="*70)
    print(f" Calligraphy Style Fourier Analysis (Samples: {sample_note})")
    if use_common_chars_only:
        print(f" 方法：只用 {len(common_chars)} 個所有書法家都寫過的共同字，排除字本身複雜度的干擾")
    print("="*70)

    styles_results = {}
    styles_std = {}
    overall_stats = {}
    # 同一位書法家可能有多本字帖（例如沈尹默有 4 本），用內部名稱逐一處理，
    # 但用顯示名稱（中文）彙總——見下方 vecs_by_display，避免後面處理的字帖
    # 覆蓋掉前面字帖的結果（過去的 bug：直接 styles_results[display_name] = ...
    # 會讓同一位書法家只剩最後處理的那本字帖，其他本的資料全部被丟棄）
    vecs_by_display = {}
    stats_by_display = {}

    for name in sorted(calligraphers):
        display_name = calligraphers_display[name]
        print(f"\n 分析: {display_name}")

        if use_common_chars_only:
            img_paths = sorted(common_char_paths.get(name, []))
        else:
            info = loader.get_calligrapher_info(name)
            img_dir = info['image_dir']
            img_paths = sorted(glob.glob(os.path.join(img_dir, "*.[pj][np]g")))

        # Limit samples if specified (skip if processing all)
        if max_samples is not None:
            img_paths = img_paths[:max_samples]

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
            # 累加進顯示名稱底下的池子，而不是直接覆蓋——同一位書法家的多本
            # 字帖，全部圖片的逐張特徵向量會先合併在一起，最後才一次算平均值
            # 跟標準差，這樣每本字帖依實際圖片數量按比例貢獻，不會有人被蓋掉
            vecs_by_display.setdefault(display_name, []).extend(all_vecs)
            s = stats_by_display.setdefault(display_name, {
                'total_images': 0, 'processed': 0, 'failed': 0, 'books': 0,
            })
            s['total_images'] += len(img_paths)
            s['processed'] += success_count
            s['failed'] += fail_count
            s['books'] += 1

            print(f"   [OK] 已處理: {success_count}/{len(img_paths)} "
                  f"(成功率: {success_count / len(img_paths) * 100:.1f}%)")
        else:
            print(f"   [Error] {display_name}: 沒有有效樣本！")

    # 彙總：同一顯示名稱下所有字帖的逐張特徵向量，一次算平均值跟標準差
    for display_name, vecs in vecs_by_display.items():
        mat = np.vstack(vecs)
        styles_results[display_name] = np.mean(mat, axis=0)
        styles_std[display_name] = np.std(mat, axis=0)

        s = stats_by_display[display_name]
        s['success_rate'] = s['processed'] / s['total_images'] * 100 if s['total_images'] else 0.0
        overall_stats[display_name] = s

    if not styles_results:
        print("[Error] 無法產生結果！")
        return

    # ====== 儲存 JSON 數據（供 Web 互動圖表使用）======
    print("\n 儲存分析數據 (JSON)...")
    sample_sizes = {name: s['processed'] for name, s in overall_stats.items()}
    _save_analysis_json(styles_results, config, styles_std, vecs_by_display,
                         sample_sizes=sample_sizes, common_char_count=len(common_chars))

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

    # 產生進階視覺化（雷達圖等）
    try:
        from src.analysis.visualization import (
            create_comprehensive_report,
            print_feature_insights
        )

        print("\n 產生進階視覺化圖表...")
        viz_files = create_comprehensive_report(styles_results, output_dir)

        print("\n 分析風格特徵洞察...")
        print_feature_insights(styles_results)

    except ImportError as e:
        print(f"   [Warning] visualization module not found: {e}")
    except Exception as e:
        print(f"   [Warning] 進階視覺化產生失敗: {e}")

    # Print processing statistics
    print("\n 處理統計:")
    print("-" * 70)
    max_name_len = max(len(name) for name in overall_stats.keys())
    for name in sorted(overall_stats.keys()):
        stats = overall_stats[name]
        books_note = f", {stats['books']} 本字帖合併" if stats['books'] > 1 else ""
        print(f"  {name:<{max_name_len}s} : {stats['processed']:3d}/{stats['total_images']:3d} "
              f"({stats['success_rate']:5.1f}%){books_note}")
    print("-" * 70)

    print(f"\n 分析完成！")
    print(f"   - 基礎報告: {report_path}")
    print(f"   - 相似度熱力圖: {os.path.join(output_dir, 'similarity_matrix.png')}")
    print(f"   - 風格雷達圖: {os.path.join(output_dir, 'style_radar_chart.png')}")
    print(f"   - 特徵解釋面板: {os.path.join(output_dir, 'feature_explanation.png')}")
    print(f"   - 特徵比較圖: {os.path.join(output_dir, 'feature_comparison_bars.png')}")
    print(f"   - 風格特徵 JSON: data/index/style_features.json")
    print(f"   - 相似度矩陣 JSON: data/index/similarity_matrix.json")
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
        max_samples = None  # 預設用共同字方法，樣本數本來就少，不需要再截斷

    print("           開始 FFT 風格分析")
    run_style_analysis(max_samples=max_samples)

    print("\n" + "="*70)
    print("[OK] 分析完成！")
    print("="*70)
    print("\n已產生報告:")
    print(f"   ./output/style_analysis_report.png        (風格比較)")
    print(f"   ./output/similarity_matrix.png             (相似度熱力圖)")
    print("="*70)
