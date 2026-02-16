import pandas as pd
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle
import json
import os

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class SameCharComparatorFinal:
    def __init__(self):
        self.df = pd.read_csv('./data/ocr_labels.csv').drop_duplicates()
        
        # 載入分析結果
        with open('./data/character_analysis.json', 'r', encoding='utf-8') as f:
            self.analysis = json.load(f)
        
        # 5個書法家共有的字
        self.target_chars = [
            '免', '嘉', '奧', '婦', '峻', '巷', '市', '從', 
            '惟', '愧', '柚', '甘', '章', '胡', '論', '越', '趙'
        ]
        
        # 書法家中文名對照
        self.artist_names = {
            'Cu_Suiliang': '褚遂良',
            'Liu_Gongquan': '柳公權',
            'Ou_Yangxun': '歐陽詢',
            'Yan_Zhenqing': '顏真卿',
            'Zhao_Mengfu': '趙孟頫',
            'Wen_Zhengmeng': '文徵明'
        }
        
        print(f"🎯 載入完成！準備比較 {len(self.target_chars)} 個共有字")
        print(f"📝 目標字符: {' '.join(self.target_chars)}")
    
    def resize_image_for_display(self, img, target_size=150):
        """縮小圖片到指定尺寸用於顯示"""
        h, w = img.shape
        max_dim = max(h, w)
        
        if max_dim > target_size:
            scale = target_size / max_dim
            new_h = int(h * scale)
            new_w = int(w * scale)
            resized_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            return resized_img
        
        return img
    
    def get_char_images(self, target_char):
        """獲取某個字的所有書法家版本 - 縮小版本"""
        char_data = self.df[self.df['character'] == target_char].copy()
        
        if len(char_data) == 0:
            print(f"❌ 找不到字符 '{target_char}'")
            return {}
        
        results = {}
        for _, row in char_data.iterrows():
            artist = row['artist']
            img_path = row['path'].replace('./', '')
            
            if Path(img_path).exists():
                try:
                    # 讀取原圖
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        # 縮小圖片用於顯示
                        small_img = self.resize_image_for_display(img, target_size=80)
                        
                        results[artist] = {
                            'image': small_img,
                            'path': img_path,
                            'filename': row['filename'],
                            'chinese_name': self.artist_names.get(artist, artist)
                        }
                except Exception as e:
                    print(f"⚠️  無法讀取 {img_path}: {e}")
            else:
                print(f"⚠️  檔案不存在: {img_path}")
        
        print(f"📸 '{target_char}' 找到 {len(results)} 個書法家版本")
        return results
    
    def create_comparison_grid(self, target_char, save_path=None):
        """創建某個字的書法家對比圖 - 小圖版本"""
        char_images = self.get_char_images(target_char)
        
        if len(char_images) < 2:
            print(f"❌ '{target_char}' 的書法家版本太少，無法比較")
            return None
        
        # 固定排列順序，確保一致性
        artist_order = ['Cu_Suiliang', 'Liu_Gongquan', 'Ou_Yangxun', 
                       'Yan_Zhenqing', 'Zhao_Mengfu', 'Wen_Zhengmeng']
        
        # 按順序排列存在的書法家
        ordered_images = {}
        for artist in artist_order:
            if artist in char_images:
                ordered_images[artist] = char_images[artist]
        
        n_artists = len(ordered_images)
        
        # 布局計算
        if n_artists <= 2:
            cols, rows = 2, 1
        elif n_artists <= 4:
            cols, rows = 2, 2
        elif n_artists <= 6:
            cols, rows = 3, 2
        else:
            cols, rows = 3, 3
        
        # 創建更小的圖表，因為圖片已經縮小了
        fig_width = cols * 3      # 從4改為3
        fig_height = rows * 3 + 1 # 從4+2改為3+1
        fig = plt.figure(figsize=(fig_width, fig_height))
        
        # 設置大標題
        fig.text(0.5, 0.92, f'字符「{target_char}」的書法風格比較', 
                ha='center', va='center',
                fontsize=18, fontweight='bold')  # 字體也小一點
        
        # 計算圖片區域的參數
        subplot_width = 0.85 / cols
        subplot_height = 0.75 / rows  # 調整高度比例
        left_margin = 0.075
        bottom_margin = 0.1
        
        # 顯示每個書法家的字
        for idx, (artist, data) in enumerate(ordered_images.items()):
            row = idx // cols
            col = idx % cols
            
            # 計算每個子圖的位置
            left = left_margin + col * subplot_width
            bottom = bottom_margin + (rows - 1 - row) * subplot_height
            
            # 創建子圖
            ax = fig.add_axes([left, bottom, subplot_width, subplot_height])
            
            img = data['image']
            chinese_name = data['chinese_name']
            
            # 顯示縮小的圖片
            ax.imshow(img, cmap='gray', interpolation='bilinear')
            
            # 書法家名稱
            ax.set_title(chinese_name, fontsize=12, fontweight='bold', 
                        pad=10)
            ax.axis('off')
            
            # 添加輕微邊框
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_linewidth(0.5)
                spine.set_color('lightgray')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none',
                       pad_inches=0.3)
            print(f"💾 已保存到: {save_path}")
        
        plt.show()
        return fig
    
    def create_all_comparisons(self, output_dir='./output/comparisons_small'):
        """為所有共有字創建比較圖"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 開始生成所有小圖比較圖...")
        
        success_count = 0
        for char in self.target_chars:
            try:
                save_path = output_path / f"小圖比較_{char}.png"
                print(f"正在處理: {char}")
                fig = self.create_comparison_grid(char, save_path)
                if fig is not None:
                    success_count += 1
                    plt.close(fig)
            except Exception as e:
                print(f"❌ 生成 '{char}' 時出錯: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"✅ 完成！成功生成 {success_count}/{len(self.target_chars)} 張小圖比較圖")
        print(f"📁 輸出位置: {output_path.absolute()}")
    
    def interactive_demo(self):
        """互動式展示"""
        print("\n" + "="*60)
        print("🎨 小圖書法字符比較器 - 互動模式")
        print("="*60)
        print(f"可選字符({len(self.target_chars)}個): {' '.join(self.target_chars)}")
        
        while True:
            print("\n" + "-"*40)
            char = input("請輸入要比較的字符 (輸入 'q' 退出): ").strip()
            
            if char.lower() == 'q':
                print("👋 再見！")
                break
            
            if char not in self.target_chars:
                print(f"❌ '{char}' 不在可比較的字符列表中")
                print(f"💡 請選擇: {' '.join(self.target_chars)}")
                continue
            
            print(f"\n🔍 正在分析「{char}」...")
            
            # 顯示比較圖
            self.create_comparison_grid(char)
            
            print(f"✅ 「{char}」分析完成！")

def main():
    """主程序"""
    print("🎨 小圖書法同字異寫比較器")
    print("="*50)
    
    try:
        comparator = SameCharComparatorFinal()
        
        # 選擇操作模式
        print("\n請選擇操作模式:")
        print("1. 互動模式 - 逐一比較字符")
        print("2. 批量模式 - 生成所有小圖比較圖")
        print("3. 單字測試 - 測試一個字符")
        
        choice = input("\n請輸入選項 [1-3]: ").strip()
        
        if choice == '1':
            comparator.interactive_demo()
        elif choice == '2':
            comparator.create_all_comparisons()
        elif choice == '3':
            test_char = input("請輸入測試字符: ").strip()
            if test_char in comparator.target_chars:
                comparator.create_comparison_grid(test_char)
            else:
                print(f"❌ '{test_char}' 不在可用列表中")
        else:
            print("❌ 無效選項")
            
    except Exception as e:
        print(f"❌ 程序錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()