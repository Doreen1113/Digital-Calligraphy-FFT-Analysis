# tools/2_ocr_reviewer_gui.py
"""
OCR 結果檢查與修正工具（GUI版）
用於檢查和修正 01 字庫的 OCR 識別結果
"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import pandas as pd
import os

class ModeSelector:
    """啟動前的模式選擇對話框"""
    def __init__(self):  
        self.mode = None
        self.root = tk.Tk()
        self.root.title("選擇檢查模式")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # 標題
        title = tk.Label(
            self.root,
            text="OCR 檢查工具",
            font=("Arial", 18, "bold"),
            fg='#2c3e50'
        )
        title.pack(pady=20)
        
        # 說明
        desc = tk.Label(
            self.root,
            text="請選擇檢查模式：",
            font=("Arial", 12)
        )
        desc.pack(pady=10)
        
        # 按鈕區
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)
        
        # 模式1：檢查全部
        btn1 = tk.Button(
            btn_frame,
            text="檢查全部\n",
            command=lambda: self.select_mode('all'),
            font=("Arial", 12, "bold"),
            bg='#3498db',
            fg='white',
            width=20,
            height=3,
            relief=tk.RAISED,
            bd=3
        )
        btn1.pack(pady=10)
        
        # 模式2：只檢查未確認
        btn2 = tk.Button(
            btn_frame,
            text="檢查剩餘未確認\n",
            command=lambda: self.select_mode('unconfirmed'),
            font=("Arial", 12, "bold"),
            bg='#27ae60',
            fg='white',
            width=20,
            height=3,
            relief=tk.RAISED,
            bd=3
        )
        btn2.pack(pady=10)
        
        # 快捷鍵
        self.root.bind('1', lambda e: self.select_mode('all'))
        self.root.bind('2', lambda e: self.select_mode('unconfirmed'))
        
        hint = tk.Label(
            self.root,
            text="快捷鍵: 按 1 或 2",
            font=("Arial", 9),
            fg='#95a5a6'
        )
        hint.pack(pady=10)
        
        self.root.mainloop()
    
    def select_mode(self, mode):
        self.mode = mode
        self.root.destroy()
    
    def get_mode(self):
        return self.mode

class OCRReviewer:
    def __init__(self, csv_path, img_dir, mode='unconfirmed'):
        self.csv_path = csv_path
        self.img_dir = img_dir
        self.mode = mode
        self.df = pd.read_csv(csv_path)
        self.df['confidence'] = self.df['confidence'].astype(float)
        
        # 根據模式篩選
        if mode == 'all':
            # 檢查全部
            self.review_indices = self.df.index.tolist()
            mode_desc = "檢查全部"
        else:
            # 只檢查未確認的（信心度低或識別失敗）
            self.review_indices = self.df[
                (self.df['confidence'] < 1) | (self.df['character'] == '?')
            ].index.tolist()
            mode_desc = "檢查未確認"
        
        if not self.review_indices:
            messagebox.showinfo("完成", "所有圖片識別信心度都很高，無需檢查！")
            return
        
        self.current_pos = 0
        self.modified_count = 0
        
        # 建立主視窗
        self.root = tk.Tk()
        self.root.title(f"OCR 檢查工具 - {mode_desc} - 共 {len(self.review_indices)} 張")
        self.root.geometry("800x900")
        
        # 頂部資訊欄
        info_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        info_frame.pack(fill=tk.X)
        
        # 模式標籤
        mode_label = tk.Label(
            info_frame,
            text=f"模式: {mode_desc}",
            font=("Arial", 11),
            fg='#ecf0f1',
            bg='#2c3e50'
        )
        mode_label.pack(pady=5)
        
        self.progress_label = tk.Label(
            info_frame, 
            text="", 
            font=("Arial", 14, "bold"),
            fg='white',
            bg='#2c3e50'
        )
        self.progress_label.pack(pady=5)
        
        # 圖片顯示區
        img_container = tk.Frame(self.root, bg='white', relief=tk.SUNKEN, bd=2)
        img_container.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        self.img_label = tk.Label(img_container, bg='white')
        self.img_label.pack(pady=10)
        
        # 檔案資訊
        self.file_info_label = tk.Label(
            self.root, 
            text="",
            font=("Courier New", 10),
            fg='#7f8c8d'
        )
        self.file_info_label.pack(pady=5)
        
        # OCR 識別結果顯示
        ocr_frame = tk.LabelFrame(self.root, text="OCR 識別結果", font=("Arial", 11, "bold"))
        ocr_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.ocr_result_label = tk.Label(
            ocr_frame,
            text="",
            font=("Microsoft YaHei", 36, "bold"),
            fg='#3498db'
        )
        self.ocr_result_label.pack(pady=10)
        
        self.confidence_label = tk.Label(
            ocr_frame,
            text="",
            font=("Arial", 10)
        )
        self.confidence_label.pack()
        
        # 輸入區
        input_frame = tk.LabelFrame(self.root, text="修正", font=("Arial", 11, "bold"))
        input_frame.pack(pady=10, padx=20, fill=tk.X)
        
        input_container = tk.Frame(input_frame)
        input_container.pack(pady=15)
        
        tk.Label(input_container, text="正確的字:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        self.entry = tk.Entry(
            input_container,
            font=("Microsoft YaHei", 28, "bold"),
            width=5,
            justify='center',
            relief=tk.SOLID,
            bd=2
        )
        self.entry.pack(side=tk.LEFT, padx=10)
        self.entry.bind('<Return>', lambda e: self.save_and_next())
        
        # 快捷提示（放這裡，只顯示一次）
        hint = tk.Label(
            input_frame,
            text="✓ Enter=保存並下一張 | Space=識別正確 | ←=上一張 | →=跳過",
            font=("Arial", 9),
            fg='#95a5a6'
        )
        hint.pack(pady=5)
        
        # 按鈕區
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)
        
        # 上一張按鈕（新增）
        self.btn_prev = tk.Button(
            btn_frame,
            text="⊲ 上一張\n(←)",
            command=self.previous_image,
            font=("Arial", 11),
            bg='#95a5a6',
            fg='white',
            width=10,
            height=2,
            relief=tk.RAISED,
            bd=3
        )
        self.btn_prev.pack(side=tk.LEFT, padx=10)
        
        # 正確按鈕（綠色）
        self.btn_correct = tk.Button(
            btn_frame,
            text="✓ 識別正確\n(Space)",
            command=self.mark_correct,
            font=("Arial", 11, "bold"),
            bg='#27ae60',
            fg='white',
            width=12,
            height=2,
            relief=tk.RAISED,
            bd=3
        )
        self.btn_correct.pack(side=tk.LEFT, padx=10)
        
        # 保存並下一張（藍色）
        self.btn_save = tk.Button(
            btn_frame,
            text="→ 保存並下一張\n(Enter)",
            command=self.save_and_next,
            font=("Arial", 11, "bold"),
            bg='#3498db',
            fg='white',
            width=15,
            height=2,
            relief=tk.RAISED,
            bd=3
        )
        self.btn_save.pack(side=tk.LEFT, padx=10)
        
        # 跳過按鈕（灰色）
        self.btn_skip = tk.Button(
            btn_frame,
            text="⊳ 跳過\n(→)",
            command=self.skip,
            font=("Arial", 11),
            bg='#95a5a6',
            fg='white',
            width=8,
            height=2,
            relief=tk.RAISED,
            bd=3
        )
        self.btn_skip.pack(side=tk.LEFT, padx=10)
        
        # 底部統計欄
        stats_frame = tk.Frame(self.root, bg='#ecf0f1', height=40)
        stats_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="",
            font=("Arial", 10),
            bg='#ecf0f1'
        )
        self.stats_label.pack(pady=10)
        
        # 鍵盤快捷鍵
        self.root.bind('<Left>', lambda e: self.previous_image())
        self.root.bind('<Right>', lambda e: self.skip())
        self.root.bind('<space>', lambda e: self.mark_correct())
        

        # 顯示第一張
        self.show_current_image()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def show_current_image(self):
        """顯示當前圖片"""
        if self.current_pos >= len(self.review_indices):
            self.finish_review()
            return
        
        # 更新上一張按鈕狀態（新增）
        if self.current_pos == 0:
            self.btn_prev.config(state='disabled')
        else:
            self.btn_prev.config(state='normal')
        
        idx = self.review_indices[self.current_pos]
        row = self.df.iloc[idx]
        
        # 更新進度
        progress_pct = (self.current_pos + 1) / len(self.review_indices) * 100
        self.progress_label.config(
            text=f"進度: {self.current_pos + 1} / {len(self.review_indices)} ({progress_pct:.1f}%)"
        )
        
        # 顯示圖片
        img_path = os.path.join(self.img_dir, row['filename'])
        if os.path.exists(img_path):
            img = Image.open(img_path)
            
            # 調整大小但保持比例
            max_size = 400
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=photo)
            self.img_label.image = photo
        else:
            self.img_label.config(text="圖片不存在", image='')
        
        # 顯示檔案名
        self.file_info_label.config(text=f"檔案: {row['filename']} (索引: {idx})")
        
        # 顯示 OCR 結果
        char = row['character']
        conf = row['confidence']
        
        self.ocr_result_label.config(text=f"{char}")
        
        # 根據信心度改變顏色
        if conf >= 0.9:
            conf_color = '#27ae60'  # 綠色
        elif conf >= 0.7:
            conf_color = '#f39c12'  # 橙色
        else:
            conf_color = '#e74c3c'  # 紅色
        
        self.confidence_label.config(
            text=f"信心度: {conf:.1%}",
            fg=conf_color
        )
        
        # 預填入當前識別結果
        self.entry.delete(0, tk.END)
        if char != '?':
            self.entry.insert(0, char)
        self.entry.focus()
        
        # 更新統計
        self.update_stats()
    
    def update_stats(self):
        """更新統計資訊"""
        remaining = len(self.review_indices) - self.current_pos
        self.stats_label.config(
            text=f"已修正: {self.modified_count} | 剩餘: {remaining}"
        )

    def previous_image(self):
        """返回上一張（新增方法）"""
        if self.current_pos > 0:
            self.current_pos -= 1
            self.show_current_image()

    def mark_correct(self):
        """標記為正確，直接跳過"""
        self.current_pos += 1
        self.show_current_image()
    
    def save_and_next(self):
        """保存修正並下一張"""
        new_char = self.entry.get().strip()
        
        if not new_char:
            messagebox.showwarning("警告", "請輸入正確的字！")
            return
        
        # 更新資料
        idx = self.review_indices[self.current_pos]
        old_char = self.df.at[idx, 'character']
        
        self.df.at[idx, 'character'] = new_char
        self.df.at[idx, 'confidence'] = 1.0  # 人工確認
        
        if old_char != new_char:
            self.modified_count += 1
        
        self.current_pos += 1
        self.show_current_image()
    
    def skip(self):
        """跳過當前圖片"""
        self.current_pos += 1
        self.show_current_image()
    
    def finish_review(self):
        """完成檢查"""
        # 保存修改
        self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
        
        messagebox.showinfo(
            "完成",
            f"檢查完成！\n\n"
            f"共檢查: {len(self.review_indices)} 張\n"
            f"已修正: {self.modified_count} 張\n\n"
            f"結果已保存到:\n{self.csv_path}"
        )
        self.root.destroy()
    
    def on_closing(self):
        """關閉視窗時確認"""
        if self.modified_count > 0:
            if messagebox.askyesno("確認", f"已修正 {self.modified_count} 張，要保存嗎？"):
                self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                messagebox.showinfo("已保存", f"修改已保存到:\n{self.csv_path}")
        self.root.destroy()


# ============ 主程式 ============
if __name__ == "__main__":
    CSV_PATH = r"C:\My_Project\Fourier_drawing\Fonts\my_fonts\csv\01.csv"
    IMG_DIR = r"C:\My_Project\Fourier_drawing\Fonts\my_fonts\01"
    
    # 檢查檔案是否存在
    if not os.path.exists(CSV_PATH):
        print(f"找不到 CSV 檔案: {CSV_PATH}")
        print("請先執行 2_create_labels.py 生成標籤檔案")
    elif not os.path.exists(IMG_DIR):
        print(f"找不到圖片目錄: {IMG_DIR}")
    else:
        print("啟動 OCR 檢查工具...")
        
        # 先選擇模式
        selector = ModeSelector()
        mode = selector.get_mode()
        
        if mode:
            # 啟動檢查工具
            OCRReviewer(CSV_PATH, IMG_DIR, mode=mode)
        else:
            print("已取消")