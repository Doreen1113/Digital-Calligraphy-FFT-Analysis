"""
風格特徵視覺化模組
提供雷達圖、特徵解釋面板等進階視覺化功能
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from typing import Dict, List, Optional
from math import pi

# 設定 matplotlib 中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'sans-serif']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False
try:
    import matplotlib
    matplotlib.font_manager._rebuild()
except:
    pass


# 特徵解釋資料
FEATURE_DESCRIPTIONS = {
    'low_freq': {
        'name': '低頻能量',
        'name_en': 'Low-freq Energy',
        'description': '反映字體的整體結構與基本形態',
        'high_meaning': '結構穩定、形態規整',
        'low_meaning': '結構變化大、形態靈活',
        'calligraphy_meaning': '低頻高表示楷書規整，低頻低表示行草自由'
    },
    'mid_freq': {
        'name': '中頻能量',
        'name_en': 'Mid-freq Energy',
        'description': '反映筆畫的粗細變化與轉折',
        'high_meaning': '筆畫變化豐富、轉折明顯',
        'low_meaning': '筆畫均勻、變化較少',
        'calligraphy_meaning': '中頻高表示筆法豐富，中頻低表示用筆單純'
    },
    'high_freq': {
        'name': '高頻能量',
        'name_en': 'High-freq Energy',
        'description': '反映筆觸細節、飛白與邊緣變化',
        'high_meaning': '細節豐富、筆觸自然',
        'low_meaning': '邊緣平滑、細節較少',
        'calligraphy_meaning': '高頻高表示筆觸生動，高頻低表示線條工整'
    },
    'centroid': {
        'name': '頻譜重心',
        'name_en': 'Spectral Centroid',
        'description': '頻譜能量分布的重心位置',
        'high_meaning': '能量集中在高頻（細節為主）',
        'low_meaning': '能量集中在低頻（結構為主）',
        'calligraphy_meaning': '重心高表示注重細節，重心低表示注重結構'
    },
    'dc_ratio': {
        'name': 'DC/基頻比',
        'name_en': 'DC/Fund. Ratio',
        'description': '直流分量與基頻的比例',
        'high_meaning': '整體形態占主導',
        'low_meaning': '週期性特徵明顯',
        'calligraphy_meaning': '比值高表示字形完整，比值低表示筆畫分明'
    },
    'slope': {
        'name': '頻譜斜率',
        'name_en': 'Spectral Slope',
        'description': '頻譜能量的衰減趨勢',
        'high_meaning': '高頻保留較多（平坦）',
        'low_meaning': '高頻衰減快（陡峭）',
        'calligraphy_meaning': '斜率高表示細節保留好，斜率低表示簡化明顯'
    },
    'hf_decay': {
        'name': '高頻衰減率',
        'name_en': 'HF Decay Rate',
        'description': '高頻部分的能量衰減速度',
        'high_meaning': '高頻快速衰減',
        'low_meaning': '高頻緩慢衰減',
        'calligraphy_meaning': '衰減快表示收筆乾淨，衰減慢表示筆觸延伸'
    }
}

# 特徵順序（對應 analyze_styles.py）
FEATURE_ORDER = ['low_freq', 'mid_freq', 'high_freq', 'centroid', 'dc_ratio', 'slope', 'hf_decay']


def plot_radar_chart(styles_results: Dict[str, np.ndarray],
                     output_path: str,
                     title: str = "書法風格特徵雷達圖") -> None:
    """
    繪製雷達圖（Radar Chart / Spider Chart）

    Args:
        styles_results: {書法家名稱: 特徵向量} 的字典
        output_path: 輸出檔案路徑
        title: 圖表標題
    """
    print(f"\n 繪製雷達圖...")

    # 特徵名稱（中文）
    feature_names = [FEATURE_DESCRIPTIONS[f]['name'] for f in FEATURE_ORDER]
    num_features = len(feature_names)

    # 計算角度
    angles = [n / float(num_features) * 2 * pi for n in range(num_features)]
    angles += angles[:1]  # 閉合圖形

    # 正規化特徵值（0-1 範圍）
    normalized_data = {}
    all_values = np.vstack(list(styles_results.values()))
    min_vals = all_values.min(axis=0)
    max_vals = all_values.max(axis=0)

    for name, features in styles_results.items():
        # Min-Max 正規化
        normalized = (features - min_vals) / (max_vals - min_vals + 1e-8)
        normalized_data[name] = np.concatenate([normalized, [normalized[0]]])  # 閉合

    # 繪製雷達圖
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='polar')

    # 顏色設定
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']

    # 繪製每位書法家的雷達線
    for idx, (name, values) in enumerate(normalized_data.items()):
        ax.plot(angles, values, 'o-', linewidth=2,
               label=name, color=colors[idx % len(colors)])
        ax.fill(angles, values, alpha=0.15, color=colors[idx % len(colors)])

    # 設定座標軸
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(feature_names, size=11)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], size=9)
    ax.grid(True, linestyle='--', alpha=0.7)

    # 標題與圖例
    plt.title(title, size=16, fontweight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)

    # 儲存
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"   [OK] 雷達圖已儲存: {output_path}")


def plot_feature_explanation(output_path: str = "./output/feature_explanation.png") -> None:
    """
    繪製特徵解釋面板

    Args:
        output_path: 輸出檔案路徑
    """
    print(f"\n 繪製特徵解釋面板...")

    fig, axes = plt.subplots(4, 2, figsize=(14, 16))
    fig.suptitle('FFT 頻譜特徵解釋', fontsize=18, fontweight='bold')

    axes = axes.flatten()

    for idx, feature_key in enumerate(FEATURE_ORDER):
        ax = axes[idx]
        info = FEATURE_DESCRIPTIONS[feature_key]

        # 移除座標軸
        ax.axis('off')

        # 標題
        title = f"{info['name']}\n{info['name_en']}"
        ax.text(0.5, 0.95, title, ha='center', va='top',
               fontsize=14, fontweight='bold',
               transform=ax.transAxes)

        # 說明文字
        content = f"""
定義：
{info['description']}

高值意義：
{info['high_meaning']}

低值意義：
{info['low_meaning']}

書法意義：
{info['calligraphy_meaning']}
        """

        ax.text(0.05, 0.75, content.strip(), ha='left', va='top',
               fontsize=10, linespacing=1.8,
               transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        # 範圍指示
        ax.add_patch(plt.Rectangle((0.05, 0.02), 0.9, 0.08,
                                   facecolor='lightblue', alpha=0.3,
                                   transform=ax.transAxes))
        ax.text(0.05, 0.06, '低', ha='left', va='center',
               fontsize=9, transform=ax.transAxes)
        ax.text(0.95, 0.06, '高', ha='right', va='center',
               fontsize=9, transform=ax.transAxes)

    # 隱藏最後一個空白子圖
    if len(FEATURE_ORDER) < len(axes):
        axes[-1].axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"   [OK] 特徵解釋面板已儲存: {output_path}")


def plot_feature_comparison_bars(styles_results: Dict[str, np.ndarray],
                                 output_path: str,
                                 figsize: tuple = (14, 10)) -> None:
    """
    繪製分組柱狀圖（每個特徵一組）

    Args:
        styles_results: {書法家名稱: 特徵向量} 的字典
        output_path: 輸出檔案路徑
        figsize: 圖表尺寸
    """
    print(f"\n 繪製特徵比較柱狀圖...")

    feature_names = [FEATURE_DESCRIPTIONS[f]['name'] for f in FEATURE_ORDER]
    calligraphers = list(styles_results.keys())
    num_features = len(feature_names)
    num_calligraphers = len(calligraphers)

    # 準備資料
    data = np.array([styles_results[name] for name in calligraphers])

    # 繪圖
    fig, ax = plt.subplots(figsize=figsize)

    # 設定柱狀圖參數
    x = np.arange(num_features)
    width = 0.8 / num_calligraphers
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']

    # 繪製每位書法家的柱子
    for i, calligrapher in enumerate(calligraphers):
        offset = width * i - (width * num_calligraphers / 2) + width / 2
        values = data[i]
        ax.bar(x + offset, values, width,
              label=calligrapher,
              color=colors[i % len(colors)],
              alpha=0.8)

    # 設定座標軸
    ax.set_xlabel('特徵', fontsize=12, fontweight='bold')
    ax.set_ylabel('特徵值', fontsize=12, fontweight='bold')
    ax.set_title('書法風格特徵比較', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(feature_names, rotation=15, ha='right')
    ax.legend(fontsize=11)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"   [OK] 柱狀圖已儲存: {output_path}")


def create_comprehensive_report(styles_results: Dict[str, np.ndarray],
                               output_dir: str = "./output") -> List[str]:
    """
    產生完整的視覺化報告（雷達圖 + 特徵解釋 + 柱狀圖）

    Args:
        styles_results: {書法家名稱: 特徵向量} 的字典
        output_dir: 輸出目錄

    Returns:
        產生的檔案路徑列表
    """
    print("\n" + "="*70)
    print(" 產生完整視覺化報告")
    print("="*70)

    os.makedirs(output_dir, exist_ok=True)
    output_files = []

    # 1. 雷達圖
    radar_path = os.path.join(output_dir, "style_radar_chart.png")
    plot_radar_chart(styles_results, radar_path)
    output_files.append(radar_path)

    # 2. 特徵解釋面板
    explanation_path = os.path.join(output_dir, "feature_explanation.png")
    plot_feature_explanation(explanation_path)
    output_files.append(explanation_path)

    # 3. 柱狀圖
    bars_path = os.path.join(output_dir, "feature_comparison_bars.png")
    plot_feature_comparison_bars(styles_results, bars_path)
    output_files.append(bars_path)

    print("\n" + "="*70)
    print(f" 完成！共產生 {len(output_files)} 個視覺化圖表")
    for path in output_files:
        print(f"   - {os.path.basename(path)}")
    print("="*70 + "\n")

    return output_files


def print_feature_insights(styles_results: Dict[str, np.ndarray]) -> None:
    """
    列印特徵洞察（找出每位書法家的突出特徵）

    Args:
        styles_results: {書法家名稱: 特徵向量} 的字典
    """
    print("\n" + "="*70)
    print(" 風格特徵洞察")
    print("="*70)

    # 計算每位書法家在各特徵的排名
    calligraphers = list(styles_results.keys())
    data = np.array([styles_results[name] for name in calligraphers])

    for idx, calligrapher in enumerate(calligraphers):
        features = data[idx]

        print(f"\n【{calligrapher}】")

        # 找出前 3 個最突出的特徵
        top_indices = np.argsort(features)[-3:][::-1]

        print("  突出特徵:")
        for rank, feat_idx in enumerate(top_indices, 1):
            feature_key = FEATURE_ORDER[feat_idx]
            feature_name = FEATURE_DESCRIPTIONS[feature_key]['name']
            value = features[feat_idx]
            meaning = FEATURE_DESCRIPTIONS[feature_key]['calligraphy_meaning']

            print(f"    {rank}. {feature_name}: {value:.3f}")
            print(f"       → {meaning}")

        # 找出最弱的特徵
        weak_idx = np.argmin(features)
        weak_key = FEATURE_ORDER[weak_idx]
        weak_name = FEATURE_DESCRIPTIONS[weak_key]['name']
        weak_value = features[weak_idx]

        print(f"\n  較弱特徵:")
        print(f"    - {weak_name}: {weak_value:.3f}")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    # 測試用範例資料
    test_data = {
        '智永': np.array([0.45, 0.32, 0.18, 0.28, 0.62, -0.15, 0.12]),
        '沈尹默': np.array([0.38, 0.35, 0.22, 0.31, 0.55, -0.12, 0.14]),
        '顏真卿': np.array([0.42, 0.38, 0.25, 0.35, 0.48, -0.10, 0.16]),
        '歐陽詢': np.array([0.48, 0.30, 0.16, 0.26, 0.65, -0.18, 0.10])
    }

    # 產生完整報告
    create_comprehensive_report(test_data, "./output")

    # 列印特徵洞察
    print_feature_insights(test_data)
