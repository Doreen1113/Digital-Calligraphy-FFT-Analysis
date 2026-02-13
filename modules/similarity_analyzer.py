"""
相似度量化模組
計算不同書法家風格之間的相似度（Cosine Similarity）
產出相似度矩陣與熱圖
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial.distance import cosine
import pandas as pd


def cosine_similarity(vec1, vec2):
    """
    計算兩個向量的餘弦相似度
    
    範圍: [0, 1]
    - 1.0 = 完全相同
    - 0.5 = 中等相似
    - 0.0 = 完全不同
    """
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    
    # 正規化向量長度
    vec1 = np.asarray(vec1)
    vec2 = np.asarray(vec2)
    
    # 處理零向量
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    
    # 計算餘弦相似度
    return 1 - cosine(vec1, vec2)


def compute_similarity_matrix(styles_results):
    """
    根據風格頻譜向量計算相似度矩陣
    
    輸入: styles_results = {
            "Yan_Zhenqing": [0.5, 0.3, 0.2, ...],
            "Liu_Gongquan": [0.4, 0.35, 0.22, ...],
            ...
         }
    
    輸出: 
        - similarity_matrix (DataFrame): N×N 相似度矩陣
        - similarity_scores (dict): 成對相似度分析
    """
    names = sorted(styles_results.keys())
    n = len(names)
    
    # 初始化相似度矩陣
    sim_matrix = np.zeros((n, n))
    
    # 計算所有成對相似度
    for i in range(n):
        for j in range(n):
            vec_i = styles_results[names[i]]
            vec_j = styles_results[names[j]]
            sim_matrix[i, j] = cosine_similarity(vec_i, vec_j)
    
    # 轉換為 DataFrame（更好看）
    df = pd.DataFrame(sim_matrix, index=names, columns=names)
    
    # 計算成對相似度分析
    similarity_scores = {}
    for i in range(n):
        for j in range(i + 1, n):
            pair = f"{names[i]} <-> {names[j]}"
            similarity_scores[pair] = sim_matrix[i, j]
    
    return df, similarity_scores


def plot_similarity_heatmap(styles_results, output_path="./output/similarity_matrix.png"):
    """
    繪製相似度熱圖
    """
    sim_df, sim_scores = compute_similarity_matrix(styles_results)
    
    # 建立圖表
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 熱圖
    sns.heatmap(sim_df, 
                annot=True, 
                fmt='.3f',
                cmap='RdYlGn',  # 紅(低) -> 黃 -> 綠(高)
                vmin=0, vmax=1,
                cbar_kws={'label': 'Cosine Similarity'},
                linewidths=2,
                linecolor='white',
                square=True,
                ax=ax,
                annot_kws={'size': 11, 'weight': 'bold'})
    
    ax.set_title('Calligraphy Style Similarity Matrix\n(Fourier Descriptor Analysis)', 
                 fontsize=14, fontweight='bold', pad=20)
    
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
    print("📊 書法風格相似度分析報告 (Cosine Similarity)")
    print("="*70)
    
    print("\n🔹 相似度矩陣 (完整):")
    print(sim_df.to_string())
    
    print("\n\n🔹 成對相似度排名:")
    sorted_scores = sorted(sim_scores.items(), key=lambda x: x[1], reverse=True)
    for i, (pair, score) in enumerate(sorted_scores, 1):
        bar = "█" * int(score * 20)
        print(f"  {i}. {pair:40s} {score:.4f} {bar}")
    
    print("\n🔹 解釋指南:")
    print("  • 相似度 > 0.8: 風格極其相近（可能同時期）")
    print("  • 相似度 0.5~0.8: 風格顯著差異但有共同特徵")
    print("  • 相似度 < 0.5: 風格差異顯著（不同派別）")
    print("="*70 + "\n")


if __name__ == "__main__":
    # 示例：若要測試，需先匯入 main.py 的 styles_results
    # 這裡暫時跳過，會在 main.py 中呼叫
    pass
