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


# 特徵解釋資料（面向觀眾的易懂版本）
FEATURE_DESCRIPTIONS = {
    'low_freq': {
        'name': '結構穩定度',
        'name_en': 'Structural Stability',
        'description': '衡量字的整體骨架是否端正工整，來自傅立葉低頻能量。',
        'high_meaning': '字形骨架穩固、間架方正',
        'low_meaning': '字形較為自由靈動、不拘一格',
        'calligraphy_meaning': '歐體、柳體等楷書此項較高；行書草書較低'
    },
    'mid_freq': {
        'name': '筆畫變化度',
        'name_en': 'Stroke Variation',
        'description': '衡量筆畫粗細、轉折、提按的豐富程度，來自傅立葉中頻能量。',
        'high_meaning': '提按明顯、筆勢變化豐富',
        'low_meaning': '用筆均勻穩定、變化較少',
        'calligraphy_meaning': '顏真卿肥瘦對比大此項高；歐陽詢用筆較均勻此項低'
    },
    'high_freq': {
        'name': '細節豐富度',
        'name_en': 'Detail Richness',
        'description': '衡量飛白、毛邊、牽絲等細微筆觸的多寡，來自傅立葉高頻能量。',
        'high_meaning': '墨色層次多、有飛白與毛邊效果',
        'low_meaning': '線條光滑乾淨、邊緣整齊',
        'calligraphy_meaning': '碑帖中保留自然書寫質感的此項較高'
    },
    'centroid': {
        'name': '細節vs結構',
        'name_en': 'Detail-Structure Balance',
        'description': '頻譜能量重心偏向細節端還是結構端，反映整體風格取向。',
        'high_meaning': '重視細節表現（裝飾性強）',
        'low_meaning': '重視整體結構（骨架為主）',
        'calligraphy_meaning': '行草書重視細節此項高；楷書重視結構此項低'
    },
    'dc_ratio': {
        'name': '字形完整度',
        'name_en': 'Form Completeness',
        'description': '衡量字的輪廓是否渾然一體，來自直流分量與基頻之比。',
        'high_meaning': '筆畫連貫、字形渾然天成',
        'low_meaning': '筆畫獨立分明、結構清晰',
        'calligraphy_meaning': '沈尹默此項最高（筆畫連貫），歐陽詢較低（筆畫分明）'
    },
    'slope': {
        'name': '細節保留度',
        'name_en': 'Detail Preservation',
        'description': '高頻能量衰減的平緩程度，反映書寫細節是否被保留下來。',
        'high_meaning': '細膩筆觸完好保存、質感豐富',
        'low_meaning': '細節簡化明顯、線條概括',
        'calligraphy_meaning': '顏真卿此項最高（細節豐富），智永較低（線條簡潔）'
    },
    'hf_decay': {
        'name': '收筆乾淨度',
        'name_en': 'Stroke Ending Cleanness',
        'description': '高頻衰減速率——衡量筆觸收尾是否乾脆。',
        'high_meaning': '收筆果斷、筆觸延伸自然',
        'low_meaning': '收筆較為拘謹、速度較慢',
        'calligraphy_meaning': '沈尹默此項最高（行氣流暢），歐陽詢較低（收筆嚴謹）'
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
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#9B59B6']

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
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#9B59B6']

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
