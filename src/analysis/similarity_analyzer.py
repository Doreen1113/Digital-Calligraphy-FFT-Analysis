"""
Similarity Quantification Module
Calculate similarity between different calligraphy styles using Cosine Similarity
Generate similarity matrix and heatmap
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial.distance import cosine
import pandas as pd

# Configure matplotlib for Chinese characters
import matplotlib.font_manager as fm
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'sans-serif']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

# Force matplotlib to use Chinese fonts
try:
    import matplotlib
    matplotlib.font_manager._rebuild()
except:
    pass


def cosine_similarity(vec1, vec2):
    """
    Calculate cosine similarity between two vectors

    Range: [0, 1]
    - 1.0 = Identical
    - 0.5 = Moderate similarity
    - 0.0 = Completely different
    """
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0

    # Normalize vector length
    vec1 = np.asarray(vec1)
    vec2 = np.asarray(vec2)

    # Handle zero vectors
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0

    # Calculate cosine similarity
    return 1 - cosine(vec1, vec2)


def compute_similarity_matrix(styles_results):
    """
    Calculate similarity matrix based on style spectrum vectors

    Apply z-score normalization first, then compute cosine similarity,
    to avoid being dominated by features with large numeric ranges (e.g., low-freq energy).
    """
    names = sorted(styles_results.keys())
    n = len(names)

    # z-score normalization: equal contribution from each feature dimension
    raw = np.array([np.asarray(styles_results[name]) for name in names])
    mean = raw.mean(axis=0)
    std = raw.std(axis=0)
    std[std < 1e-10] = 1  # Avoid division by zero
    standardized = {name: (np.asarray(styles_results[name]) - mean) / std
                    for name in names}

    # Calculate pairwise similarities (z-score + cosine = Pearson correlation, range [-1,1])
    # Map to [0, 1]: (1 + r) / 2
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            raw_sim = cosine_similarity(standardized[names[i]],
                                        standardized[names[j]])
            sim_matrix[i, j] = (1 + raw_sim) / 2  # Map to [0, 1]

    df = pd.DataFrame(sim_matrix, index=names, columns=names)

    similarity_scores = {}
    for i in range(n):
        for j in range(i + 1, n):
            pair = f"{names[i]} <-> {names[j]}"
            similarity_scores[pair] = sim_matrix[i, j]

    return df, similarity_scores


def plot_similarity_heatmap(styles_results, output_path="./output/similarity_matrix.png"):
    """
    Generate similarity heatmap
    """
    sim_df, sim_scores = compute_similarity_matrix(styles_results)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Heatmap
    sns.heatmap(sim_df,
                annot=True,
                fmt='.3f',
                cmap='RdYlGn',  # Red (low) -> Yellow -> Green (high)
                vmin=0, vmax=1,
                cbar_kws={'label': 'Cosine Similarity'},
                linewidths=2,
                linecolor='white',
                square=True,
                ax=ax,
                annot_kws={'size': 11, 'weight': 'bold'})

    ax.set_title('Calligraphy Style Similarity Matrix\n(Fourier Descriptor Analysis)',
                 fontsize=14, fontweight='bold', pad=20)

    # Rotate labels
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"[OK] Similarity heatmap generated: {output_path}")

    return sim_df, sim_scores


def print_similarity_report(sim_df, sim_scores):
    """
    Print similarity analysis report
    """
    print("\n" + "="*70)
    print(" Calligraphy Style Similarity Analysis (Cosine Similarity)")
    print("="*70)

    print("\n Similarity Matrix (Complete):")
    # Calculate column widths for alignment
    names = list(sim_df.index)
    max_name_len = max(len(str(name)) for name in names)

    # Print header
    header = " " * (max_name_len + 2)
    for name in names:
        header += f"{name:>12s} "
    print(header)

    # Print matrix rows
    for i, name in enumerate(names):
        row = f"  {name:<{max_name_len}s} "
        for j in range(len(names)):
            row += f"{sim_df.iloc[i, j]:11.6f} "
        print(row)

    print("\n Pairwise Similarity Ranking:")
    sorted_scores = sorted(sim_scores.items(), key=lambda x: x[1], reverse=True)
    max_pair_len = max(len(pair) for pair, _ in sorted_scores) if sorted_scores else 40

    for i, (pair, score) in enumerate(sorted_scores, 1):
        bar = "#" * int(score * 20)
        print(f"  {i}. {pair:<{max_pair_len}s} {score:.4f} {bar}")

    print("\n Interpretation Guide:")
    print("  * Similarity > 0.8: Extremely similar style (possibly same period)")
    print("  * Similarity 0.5~0.8: Significant differences but common features")
    print("  * Similarity < 0.5: Distinct style differences (different schools)")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Example: To test, need to import styles_results from main.py
    # Skip for now, will be called from main.py
    pass
