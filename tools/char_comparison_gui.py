import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import cv2
import numpy as np
from pathlib import Path
import json

class CharComparisonGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎨 書法同字異寫比較器")
        self.root.geometry("1000x700")
        
        # 載入數據
        self.df = pd.read_csv('./data/ocr_labels.csv').drop_duplicates()
        self.target_chars = [
            '免', '嘉', '奧', '婦', '峻', '巷', '市', '從', 
            '惟', '愧', '柚', '甘', '章', '胡', '論', '越', '趙'
        ]
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置UI界面"""
        # 標題
        title_label = tk.Label(self.root, text="書法同字異寫比較器", 
                              font=('Microsoft JhengHei', 16, 'bold'))
        title_label.pack(pady=10)
        
        # 說明文字
        desc_label = tk.Label(self.root, 
                             text="選擇一個字符，查看5個書法家的不同風格寫法", 
                             font=('Microsoft JhengHei', 10))
        desc_label.pack(pady=5)
        
        # 字符選擇框
        select_frame = tk.Frame(self.root)
        select_frame.pack(pady=10)
        
        tk.Label(select_frame, text="選擇字符:", 
                font=('Microsoft JhengHei', 12)).pack(side=tk.LEFT, padx=5)
        
        self.char_var = tk.StringVar(value=self.target_chars[0])
        self.char_combo = ttk.Combobox(select_frame, textvariable=self.char_var,
                                      values=self.target_chars, font=('Microsoft JhengHei', 12))
        self.char_combo.pack(side=tk.LEFT, padx=5)
        
        compare_btn = tk.Button(select_frame, text="🔍 比較", 
                               command=self.compare_character,
                               font=('Microsoft JhengHei', 10, 'bold'),
                               bg='lightblue')
        compare_btn.pack(side=tk.LEFT, padx=10)
        
        # 結果顯示區域
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 狀態欄
        self.status_var = tk.StringVar(value="準備就緒")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def get_char_images(self, target_char):
        """獲取字符圖片"""
        char_data = self.df[self.df['character'] == target_char].copy()
        
        results = {}
        for _, row in char_data.iterrows():
            artist = row['artist']
            img_path = row['path'].replace('./', '')
            
            if Path(img_path).exists():
                try:
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        results[artist] = {
                            'image': img,
                            'path': img_path,
                            'filename': row['filename']
                        }
                except:
                    continue
                    
        return results
    
    def compare_character(self):
        """比較選中的字符"""
        char = self.char_var.get()
        self.status_var.set(f"正在分析 '{char}'...")
        
        try:
            char_images = self.get_char_images(char)
            
            if len(char_images) < 2:
                messagebox.showwarning("警告", f"字符 '{char}' 的書法家版本太少")
                return
            
            # 清除舊的畫布
            for widget in self.canvas_frame.winfo_children():
                widget.destroy()
            
            # 創建matplotlib圖
            n_artists = len(char_images)
            cols = min(3, n_artists)
            rows = (n_artists + cols - 1) // cols
            
            plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei']
            fig, axes = plt.subplots(rows, cols, figsize=(12, 8))
            
            if n_artists == 1:
                axes = [axes]
            elif rows == 1:
                axes = axes.reshape(1, -1)
            
            fig.suptitle(f"字符 '{char}' 的書法風格比較", fontsize=16, fontweight='bold')
            
            for idx, (artist, data) in enumerate(char_images.items()):
                row = idx // cols
                col = idx % cols
                
                if rows == 1:
                    ax = axes[col]
                else:
                    ax = axes[row, col]
                
                img = data['image']
                ax.imshow(img, cmap='gray')
                ax.set_title(f"{artist}", fontsize=12, fontweight='bold')
                ax.axis('off')
            
            # 隱藏多餘的子圖
            for idx in range(n_artists, rows * cols):
                row = idx // cols
                col = idx % cols
                if rows == 1:
                    axes[col].axis('off')
                else:
                    axes[row, col].axis('off')
            
            plt.tight_layout()
            
            # 嵌入到Tkinter
            canvas = FigureCanvasTkAgg(fig, self.canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            self.status_var.set(f"'{char}' 比較完成！找到 {len(char_images)} 個書法家版本")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"分析出錯: {str(e)}")
            self.status_var.set("發生錯誤")

def main():
    root = tk.Tk()
    app = CharComparisonGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()