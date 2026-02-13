"""
相似度量化模組
計算不同書法家風格之間的相似度（加權餘弦相似度）
產出相似度矩陣與熱圖

改進說明:
- 使用加權餘弦相似度，突顯低頻（結構）特徵的重要性
- 低頻 (0-5): 權重 2.0 - 筆畫粗細、整體結構
- 中頻 (6-12): 權重 1.5 - 筆畫轉折、細節
- 高頻 (>12): 權重 1.0 - 紋理、邊緣
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial.distance import cosine
import pandas as pd


def get_frequency_weights(vec_length):
    """
    生成頻率權重向量
    
    設計理念：
    - 書法風格的主要差異在低頻（筆畫粗細、結構）
    - 高頻多為噪聲和紙張紋理
    - 通過加權突顯重要特徵
    
    返回：權重向量，與輸入向量等長
    """
    weights = np.ones(vec_length)
    
    for i in range(vec_length):
        if i <= 5:  # 低頻：結構特徵
            weights[i] = 2.0
        elif i <= 12:  # 中頻：筆畫細節
            weights[i] = 1.5
        else:  # 高頻：紋理細節
            weights[i] = 1.0
    
    return weights


def weighted_cosine_similarity(vec1, vec2):
    """
    計算加權餘弦相似度
    
    範圍: [0, 1]
    - 1.0 = 完全相同
    - 0.5~0.8 = 中等相似（同派別不同家）
    - 0.3~0.5 = 顯著差異（不同派別）
    - < 0.3 = 完全不同
    """
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    
    vec1 = np.asarray(vec1)
    vec2 = np.asarray(vec2)
    
    # 處理零向量
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    
    # 獲取權重
    weights = get_frequency_weights(len(vec1))
    
    # 加權向量
    weighted_vec1 = vec1 * weights
    weighted_vec2 = vec2 * weights
    
    # 計算加權餘弦相似度
    dot_product = np.dot(weighted_vec1, weighted_vec2)
    norm1 = np.linalg.norm(weighted_vec1)
    norm2 = np.linalg.norm(weighted_vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def cosine_similarity(vec1, vec2):
    """
    傳統餘弦相似度（保留以便對比）
    """
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    
    vec1 = np.asarray(vec1)
    vec2 = np.asarray(vec2)
    
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    
    return 1 - cosine(vec1, vec2)


def compute_similarity_matrix(styles_results, use_weighted=True):
    """
    根據風格頻譜向量計算相似度矩陣
    
    輸入: 
        styles_results = {
            "Yan_Zhenqing": [0.5, 0.3, 0.2, ...],
            "Liu_Gongquan": [0.4, 0.35, 0.22, ...],
            ...
         }
        use_weighted: 是否使用加權相似度（預設 True）
    
    輸出: 
        - similarity_matrix (DataFrame): N×N 相似度矩陣
        - similarity_scores (dict): 成對相似度分析
    """
    names = sorted(styles_results.keys())
    n = len(names)
    
    # 選擇相似度函數
    sim_func = weighted_cosine_similarity if use_weighted else cosine_similarity
    
    # 初始化相似度矩陣
    sim_matrix = np.zeros((n, n))
    
    # 計算所有成對相似度
    for i in range(n):
        for j in range(n):
            vec_i = styles_results[names[i]]
            vec_j = styles_results[names[j]]
            sim_matrix[i, j] = sim_func(vec_i, vec_j)
    
    # 轉換為 DataFrame
    df = pd.DataFrame(sim_matrix, index=names, columns=names)
    
    # 計算成對相似度分析
    similarity_scores = {}
    for i in range(n):
        for j in range(i + 1, n):
            pair = f"{names[i]} <-> {names[j]}"
            similarity_scores[pair] = sim_matrix[i, j]
    
    return df, similarity_scores


def plot_similarity_heatmap(styles_results, output_path="./output/similarity_matrix.png", use_weighted=True):
    """
    繪製相似度熱圖
    """
    sim_df, sim_scores = compute_similarity_matrix(styles_results, use_weighted)
    
    # 建立圖表
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 熱圖
    sns.heatmap(sim_df, 
                annot=True, 
                fmt='.3f',
                cmap='RdYlGn',  # 紅(低) -> 黃 -> 綠(高)
                vmin=0, vmax=1,
                cbar_kws={'label': 'Weighted Cosine Similarity' if use_weighted else 'Cosine Similarity'},
                linewidths=2,
                linecolor='white',
                square=True,
                ax=ax,
                annot_kws={'size': 11, 'weight': 'bold'})
    
    title = 'Calligraphy Style Similarity Matrix\n'
    title += '(Weighted Fourier Analysis)' if use_weighted else '(Fourier Descriptor Analysis)'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    # 旋轉標籤
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ 相似度熱圖已生成: {output_path}")
    
    return sim_df, sim_scores


def print_similarity_report(sim_df, sim_scores):
    """
    列印相似度分析報告
    """
    print("\n" + "="*70)
    print("📊 書法風格相似度分析報告 (Weighted Cosine Similarity)")
    print("="*70)
    
    print("\n🔹 相似度矩陣 (完整):")
    print(sim_df.to_string())
    
    print("\n\n🔹 成對相似度排名:")
    sorted_scores = sorted(sim_scores.items(), key=lambda x: x[1], reverse=True)
    for i, (pair, score) in enumerate(sorted_scores, 1):
        bar = "█" * int(score * 20)
        print(f"  {i}. {pair:40s} {score:.4f} {bar}")
    
    print("\n🔹 解釋指南 (加權相似度):")
    print("  • 相似度 > 0.8: 風格極其相近（同時期同派別）")
    print("  • 相似度 0.5~0.8: 風格相近但有差異（同派別不同家）")
    print("  • 相似度 0.3~0.5: 風格顯著差異（不同派別）")
    print("  • 相似度 < 0.3: 風格完全不同")
    print("\n🔹 書法史預期:")
    print("  • 柳公權 vs 歐陽詢應 > 柳公權 vs 顏真卿（瘦硬派 vs 肥厚派）")
    print("  • 歐陽詢 vs 顏真卿應為中等差異（同為唐楷）")
    print("="*70 + "\n")


if __name__ == "__main__":
    pass
