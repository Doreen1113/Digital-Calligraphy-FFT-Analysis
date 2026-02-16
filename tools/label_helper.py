"""
OCR輔助書法標註工具
使用PaddleOCR識別書法字，人工審核修正
"""
import os
import json
import csv

def create_sample_labels():
    """創建示例標籤文件"""
    # 從前面的分析，我們知道褚遂良有860張
    # 先手動標註前30張作為示例
    
    sample_labels = {
        "data/Cu_Suiliang/0001.jpg": "永",
        "data/Cu_Suiliang/0002.jpg": "一",
        "data/Cu_Suiliang/0003.jpg": "之",
        # ... 可以繼續添加
    }
    
    # 保存為CSV
    with open('./data/sample_labels.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['path', 'character'])
        for path, char in sample_labels.items():
            writer.writerow([path, char])
    
    print("✅ 示例標籤已創建: ./data/sample_labels.csv")
    return _ocr_instance
    print("請在此基礎上手動添加更多標籤")

def quick_label_common_chars():
    """快速標註常見字"""
    print("=" * 70)
    print("快速標註 - 只標註最常見的60個字")
    print("=" * 70)
    
    common_chars = [
        "永", "一", "之", "也", "者", "為", "有", "無", "大", "小",
        "中", "天", "地", "人", "王", "主", "文", "字", "言", "心",
        "手", "月", "日", "水", "火", "木", "金", "土", "風", "雨",
        "雲", "龍", "書", "法", "道", "德", "仁", "義", "禮", "智",
        "信", "和", "平", "安", "樂", "福", "壽", "喜", "春", "夏",
        "秋", "冬", "東", "西", "南", "北", "上", "下", "左", "右"
    ]
    
    print(f"\n目標字符（共{len(common_chars)}個）：")
    print("".join(common_chars))
    
    print("\n\n請在Kaggle原始數據頁面查找是否有字符標籤")
    print("或手動為前100張圖片標註這些字")
    
    # 創建模板
    with open('./data/label_template.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['path', 'artist', 'filename', 'character', 'notes'])
        
        # 為每位書法家創建前10張的模板
        artists = ['Cu_Suiliang', 'Liu_Gongquan', 'Ou_Yangxun', 
                  'Wen_Zhengmeng', 'Yan_Zhenqing', 'Zhao_Mengfu']
        
        for artist in artists:
            for i in range(1, 11):
                filename = f"{i:04d}.jpg"
                path = f"data/{artist}/{filename}"
                writer.writerow([path, artist, filename, '', ''])
    
    print("\n✅ 標註模板已創建: ./data/label_template.csv")
    print("請用Excel打開，在character列填入對應的字")

if __name__ == "__main__":
    print("書法圖片標註助手")
    print("=" * 70)
    print("\n選項：")
    print("1. 創建標註模板（用Excel手動填寫）")
    print("2. 創建示例標籤")
    print("\n建議流程：")
    print("  1) 先執行選項1，生成Excel模板")
    print("  2) 手動標註前60張（每位書法家前10張）")
    print("  3) 查看這60張是否有規律")
    print("  4) 根據規律批量處理剩餘圖片")
    
    choice = input("\n請選擇 (1/2): ").strip()
    
    if choice == "1":
        quick_label_common_chars()
    elif choice == "2":
        create_sample_labels()
    else:
        print("無效選擇")
