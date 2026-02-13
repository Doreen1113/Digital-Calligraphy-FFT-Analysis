"""
頻譜指紋圖模組
生成多位書法家的平均頻譜曲線疊疑圖

核心價值：
- 直觀展示不同書法家的風格差異
- 使用對數座標軸突顯低頻（結構）與高頻（細節）的差異
- 比直條圖更有說服力

預期發現：
- 顏真卿：低頻能量高（筆畫粗壯）
- 柳公權：高頻衰減快（筆畫乾淨俊俐）
- 歐陽詢：介於兩者之間（嚴謹規矩）
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os


def plot_spectrum_fingerprint(styles_results, output_path="./output/spectrum_fingerprint.png", max_freq=20):
    """
    繪製頻譜指紋曲線圖（多條曲線疊疑）
    
    參數：
        styles_results: dict, {name: frequency_vector}
        output_path: str, 輸出檔案路徑
        max_freq: int, 顯示的最大頻率索引
    
    設計說明：
        - X軸：頻率索引 (0=DC分量/結構, >5=筆畫細節)
        - Y軸：正規化振幅 (對數坐標，突顯差異)
        - 多條曲線：每位書法家一條，不同顏色
    """
    # 註冊 matplotlib 的 DejaVu Sans 字體
    try:
        import matplotlib
        data_path = matplotlib.get_data_path()
        dejavu_path = os.path.join(data_path, 'fonts', 'ttf', 'DejaVuSans.ttf')
        if os.path.exists(dejavu_path):
            fm.fontManager.addfont(dejavu_path)
            fp = fm.FontProperties(fname=dejavu_path)
            plt.rcParams['font.family'] = fp.get_name()
    except Exception:
        pass
    
    # 建立圖表
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 專業配色方案
    colors = {
        'Yan_Zhenqing': '#E74C3C',    # 紅色 - 肥厚派
        'Liu_Gongquan': '#3498DB',    # 藍色 - 瘦硬派
        'Ou_Yangxun': '#2ECC71',      # 綠色 - 嚴謹派
        'Wang_Xizhi': '#9B59B6',      # 紫色 - 行書大師
        'Zhao_Mengfu': '#F39C12',     # 橘色 - 元代楷書
        'Mi_Fu': '#1ABC9C'            # 青色 - 宋代行書
    }
    
    # 預設顏色 (如果名字不在 colors 中)
    default_colors = ['#34495E', '#95A5A6', '#E67E22']
    
    # 繪製每位書法家的曲線
    names = sorted(styles_results.keys())
    for i, name in enumerate(names):
        vec = np.asarray(styles_results[name])[:max_freq]
        
        # 避免零值導致 log 錯誤
        vec = np.clip(vec, 1e-8, None)
        
        # X 軸：頻率索引
        x = np.arange(len(vec))
        
        # 選擇顏色
        color = colors.get(name, default_colors[i % len(default_colors)])
        
        # 繪製曲線
        ax.plot(x, vec, 
                label=name.replace('_', ' '),  # 移除下劃線更美觀
                linewidth=2.5,
                marker='o', 
                markersize=6,
                markerfacecolor=color,
                markeredgewidth=1.2,
                markeredgecolor='white',
                color=color,
                alpha=0.85,
                zorder=3)
    
    # 標題與子標題
    fig.suptitle('Calligraphy Style Spectrum Fingerprint', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # 軸標籤
    ax.set_xlabel('Frequency Index (0=Structure, >5=Stroke Details, >12=Texture)', 
                  fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Normalized Magnitude (Log Scale)', 
                  fontsize=12, fontweight='bold', labelpad=10)
    
    # 設定 Y 軸為對數坐標（突顯差異）
    ax.set_yscale('log')
    
    # X 軸範圍
    ax.set_xlim(-0.5, max_freq - 0.5)
    ax.set_xticks(range(0, max_freq, 2))  # 每 2 個顯示一次
    
    # 網格線（比直條圖更清楚）
    ax.grid(True, which='major', linestyle='-', linewidth=0.8, alpha=0.3, zorder=0, color='#999999')
    ax.grid(True, which='minor', linestyle=':', linewidth=0.4, alpha=0.15, zorder=0, color='#cccccc')
    ax.minorticks_on()
    
    # 美化邊框
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_visible(True)
        ax.spines[spine].set_linewidth(1.5)
        ax.spines[spine].set_color('#333333')
    
    # Tick 樣式
    ax.tick_params(axis='both', which='major', labelsize=10, width=1.5, length=6, colors='#333333')
    ax.tick_params(axis='both', which='minor', labelsize=9, width=1.0, length=3, colors='#666666')
    
    # 圖例（右上角）
    legend = ax.legend(frameon=True, loc='upper right', fontsize=11, 
                       framealpha=0.95, edgecolor='#333333', fancybox=True, 
                       shadow=True, title='Calligrapher')
    legend.get_title().set_fontweight('bold')
    legend.get_title().set_fontsize(12)
    legend.get_frame().set_linewidth(1.5)
    legend.get_frame().set_facecolor('#ffffff')
    
    # 調整佈局
    plt.subplots_adjust(left=0.10, right=0.95, top=0.92, bottom=0.12)
    
    # 儲存圖片
    saved = False
    for dpi in [150, 100, 72]:
        try:
            fig.savefig(output_path, dpi=dpi, facecolor='white', edgecolor='none')
            saved = True
            print(f"✅ 頻譜指紋圖已生成 (DPI={dpi}): {output_path}")
            break
        except Exception as e:
            if dpi == 72:
                print(f"❌ 無法保存頻譜指紋圖: {e}")
            continue
    
    plt.close(fig)
    
    if not saved:
        print(f"⚠️ 頻譜指紋圖儲存失敗")
    
    return saved


def analyze_spectrum_differences(styles_results, max_freq=20):
    """
    分析並列印頻譜差異的詳細報告
    
    輸出示例：
        - 顏真卿的低頻能量 (0-5) 比柳公權高 12%
        - 柳公權的高頻衰減 (12-20) 比顏真卿快 35%
    """
    print("\n" + "="*70)
    print("🔍 頻譜指紋差異分析")
    print("="*70)
    
    names = sorted(styles_results.keys())
    
    for name in names:
        vec = np.asarray(styles_results[name])[:max_freq]
        
        # 計算不同頻段的能量
        low_freq_energy = np.sum(vec[:6])      # 0-5: 結構
        mid_freq_energy = np.sum(vec[6:13])    # 6-12: 筆畫
        high_freq_energy = np.sum(vec[13:])    # 13+: 細節
        
        total_energy = low_freq_energy + mid_freq_energy + high_freq_energy
        
        # 計算比例
        low_pct = (low_freq_energy / total_energy) * 100 if total_energy > 0 else 0
        mid_pct = (mid_freq_energy / total_energy) * 100 if total_energy > 0 else 0
        high_pct = (high_freq_energy / total_energy) * 100 if total_energy > 0 else 0
        
        print(f"\n🔹 {name.replace('_', ' ')}:")
        print(f"   低頻能量 (0-5, 結構):   {low_pct:5.1f}%  " + "█" * int(low_pct / 5))
        print(f"   中頻能量 (6-12, 筆畫):  {mid_pct:5.1f}%  " + "█" * int(mid_pct / 5))
        print(f"   高頻能量 (13+, 細節):   {high_pct:5.1f}%  " + "█" * int(high_pct / 5))
    
    print("\n" + "="*70)
    print("💡 解讀指南:")
    print("  • 低頻比例高 → 筆畫粗壯、結構穩重（如顏體）")
    print("  • 中頻比例高 → 筆畫轉折明顯、細節豐富")
    print("  • 高頻比例低 → 筆畫乾淨俊俐（如柳體）")
    print("="*70 + "\n")


if __name__ == "__main__":
    # 範例：測試使用
    print("⚠️  此模組應在 main.py 中呼叫")
    print("用法：")
    print("  from modules.spectrum_fingerprint import plot_spectrum_fingerprint, analyze_spectrum_differences")
    print("  plot_spectrum_fingerprint(styles_results, './output/spectrum_fingerprint.png')")
    print("  analyze_spectrum_differences(styles_results)")
