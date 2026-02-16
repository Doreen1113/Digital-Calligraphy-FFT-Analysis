"""
簡易書法圖片標註工具（純終端版）
用途：快速標註每張圖片是什麼字，建立字典索引
"""

import os
import pandas as pd
from pathlib import Path
import json

# 配置
DATA_DIR = "./data"
LABEL_FILE = "./data/image_labels.csv"
PROGRESS_FILE = "./data/label_progress.json"

def load_progress():
    """載入標註進度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_progress(progress):
    """保存標註進度"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def load_existing_labels():
    """載入已有標籤"""
    if os.path.exists(LABEL_FILE):
        df = pd.read_csv(LABEL_FILE, encoding='utf-8')
        return df
    return pd.DataFrame(columns=['path', 'artist', 'filename', 'character', 'notes'])

# ============ 文件操作 ============

def get_all_images() -> List[Dict]:
    """獲取所有圖片"""
    images = []
    artists = ['Cu_Suiliang', 'Liu_Gongquan', 'Ou_Yangxun', 
               'Wen_Zhengmeng', 'Yan_Zhenqing', 'Zhao_Mengfu']
    
    for artist in artists:
        artist_dir = os.path.join(DATA_DIR, artist)
        if os.path.exists(artist_dir):
            for file in sorted(os.listdir(artist_dir)):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    images.append({
                        'path': os.path.join(artist_dir, file),
                        'artist': artist,
                        'filename': file
                    })
    
    return images

def load_progress() -> Dict:
    """載入進度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'completed': [], 'labels': {}}

def save_progress(progress: Dict):
    """保存進度"""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

# ============ 批量識別 ============

def batch_ocr_recognize(num_samples: int = 100, artist_filter: str = None):
    """
    批量OCR識別
    
    Args:
        num_samples: 每次處理多少張
        artist_filter: 只處理特定書法家
    """
    print("=" * 70)
    print("📖 OCR批量識別模式")
    print("=" * 70)
    
    # 檢查OCR是否可用
    if get_ocr() is None:
        return
    
    images = get_all_images()
    progress = load_progress()
    completed = set(progress.get('completed', []))
    
    # 篩選
    if artist_filter:
        images = [img for img in images if img['artist'] == artist_filter]
    
    # 選擇未處理的圖片
    pending = [img for img in images if img['path'] not in completed]
    
    print(f"總圖片數: {len(images)}")
    print(f"已處理: {len(completed)}")
    print(f"待處理: {len(pending)}")
    
    if not pending:
        print("✅ 全部處理完成！")
        return
    
    # 處理指定數量
    batch = pending[:num_samples]
    
    results = []
    for i, img in enumerate(batch):
        print(f"\r處理中 [{i+1}/{len(batch)}]: {img['artist']}/{img['filename']}", end='', flush=True)
        
        # OCR識別
        char, confidence = ocr_recognize(img['path'])
        
        results.append({
            'path': img['path'],
            'artist': img['artist'],
            'filename': img['filename'],
            'ocr_result': char or '?',
            'confidence': f"{confidence:.2f}" if confidence else "0.00",
            'verified': 'False'
        })
        
        # 更新進度
        progress['completed'].append(img['path'])
        progress['labels'][img['path']] = char or '?'
    
    print("\n")
    
    # 保存進度
    save_progress(progress)
    
    # 輸出CSV供審核
    batch_num = len(completed) // num_samples + 1
    output_file = f"./data/ocr_batch_{batch_num:03d}.csv"
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'artist', 'filename', 'ocr_result', 'confidence', 'verified'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✅ 識別結果已保存: {output_file}")
    
    # 統計
    recognized = sum(1 for r in results if r['ocr_result'] != '?')
    high_conf = sum(1 for r in results if float(r['confidence']) > 0.8)
    
    print(f"\n📊 本批次統計：")
    print(f"   成功識別: {recognized}/{len(results)} ({100*recognized/len(results):.1f}%)")
    print(f"   高置信度(>80%): {high_conf}/{len(results)} ({100*high_conf/len(results):.1f}%)")
    
    # 顯示部分結果
    print(f"\n📝 部分識別結果：")
    for r in results[:10]:
        conf_bar = "🟢" if float(r['confidence']) > 0.8 else "🟡" if float(r['confidence']) > 0.5 else "🔴"
        print(f"   {conf_bar} {r['filename']}: 【{r['ocr_result']}】 ({r['confidence']})")
    
    print(f"\n下一步：")
    print(f"   1. 用 Excel 打開 {output_file}")
    print(f"   2. 檢查 ocr_result 欄位，修正錯誤")
    print(f"   3. 將 verified 改為 True")
    print(f"   4. 執行選項4合併標籤")

def label_images_batch():
    """批次標註模式（一次標註多張）"""
    print("=" * 70)
    print("批次標註模式")
    print("=" * 70)
    print("說明：連續輸入多個字，用空格分隔，數量要與圖片數量相同")
    print("例如：永 和 美 好 （標註4張圖）")
    print("=" * 70)
    
    df = load_existing_labels()
    existing_labels = set(df['path'].tolist()) if not df.empty else set()
    
    images = get_all_images()
    unlabeled = [img for img in images if img['path'] not in existing_labels]
    
    print(f"\n共有 {len(images)} 張圖片")
    print(f"已標註 {len(existing_labels)} 張")
    print(f"待標註 {len(unlabeled)} 張\n")
    
    if len(unlabeled) == 0:
        print("所有圖片都已標註完成！")
        return
    
    # 按書法家分組
    by_artist = {}
    for img in unlabeled:
        artist = img['artist']
        if artist not in by_artist:
            by_artist[artist] = []
        by_artist[artist].append(img)
    
    labels_list = df.to_dict('records') if not df.empty else []
    
    for artist, imgs in by_artist.items():
        print(f"\n【{artist}】共 {len(imgs)} 張待標註")
        print(f"圖片列表: {', '.join([img['filename'] for img in imgs[:10]])}")
        if len(imgs) > 10:
            print(f"... 還有 {len(imgs)-10} 張")
        
        response = input(f"\n是否標註這些圖片？(y/n/skip): ").strip().lower()
        
        if response == 'skip' or response == 'n':
            print("跳過此書法家")
            continue
        elif response != 'y':
            continue
        
        # 批次輸入
        print(f"\n請輸入 {len(imgs)} 個字，用空格分隔:")
        print(f"（對應順序: {', '.join([img['filename'] for img in imgs[:5]])}{'...' if len(imgs) > 5 else ''}）")
        
        chars_input = input("> ").strip()
        chars = chars_input.split()
        
        if len(chars) != len(imgs):
            print(f"❌ 字數不符！需要 {len(imgs)} 個字，你輸入了 {len(chars)} 個")
            continue
        
        # 確認
        print("\n確認標註:")
        for i, (img, char) in enumerate(zip(imgs, chars)):
            print(f"  {img['filename']} → {char}")
        
        confirm = input("\n確認無誤？(y/n): ").strip().lower()
        if confirm != 'y':
            print("取消標註")
            continue
        
        # 保存
        for img, char in zip(imgs, chars):
            label_entry = {
                'path': img['path'],
                'artist': img['artist'],
                'filename': img['filename'],
                'character': char,
                'notes': ''
            }
            labels_list.append(label_entry)
        
        print(f"✅ 已標註 {len(imgs)} 張")
        
        # 保存進度
        df_temp = pd.DataFrame(labels_list)
        df_temp.to_csv(LABEL_FILE, index=False, encoding='utf-8')
        print(f"已保存至 {LABEL_FILE}")
    
    print(f"\n✅ 標註完成！共 {len(labels_list)} 條")

def analyze_labels():
    """分析標籤統計"""
    if not os.path.exists(LABEL_FILE):
        print("尚未開始標註")
        return
    
    df = pd.read_csv(LABEL_FILE, encoding='utf-8')
    
    print("\n" + "=" * 70)
    print("標註統計")
    print("=" * 70)
    print(f"總標籤數: {len(df)}")
    print(f"\n各書法家標註數量:")
    artist_counts = df['artist'].value_counts()
    for artist, count in artist_counts.items():
        print(f"  {artist}: {count} 張")
    
    print(f"\n出現次數最多的字（前30）:")
    char_counts = df['character'].value_counts().head(30)
    for char, count in char_counts.items():
        print(f"  {char}: {count} 次")
    
    print(f"\n多位書法家共同寫過的字:")
    char_artist_counts = df.groupby('character')['artist'].nunique()
    
    for min_artists in [6, 5, 4, 3]:
        common_chars = char_artist_counts[char_artist_counts >= min_artists].sort_values(ascending=False)
        if len(common_chars) > 0:
            print(f"\n  至少{min_artists}位書法家都寫過的字 ({len(common_chars)} 個):")
            for char, count in common_chars.head(20).items():
                artists = df[df['character'] == char]['artist'].unique()
                artists_str = ', '.join(sorted(artists))
                print(f"    「{char}」: {count}位 → {artists_str}")
            break
    else:
        print("  尚未找到多位書法家共同寫過的字，繼續標註更多圖片")

def export_character_index():
    """導出字典索引（字→書法家→圖片路徑）"""
    if not os.path.exists(LABEL_FILE):
        print("尚未開始標註")
        return
    
    df = pd.read_csv(LABEL_FILE, encoding='utf-8')
    
    # 建立索引
    char_index = {}
    for _, row in df.iterrows():
        char = row['character']
        artist = row['artist']
        path = row['path']
        
        if char not in char_index:
            char_index[char] = {}
        if artist not in char_index[char]:
            char_index[char][artist] = []
        char_index[char][artist].append(path)
    
    # 保存索引
    index_file = "./data/character_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(char_index, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 字典索引已保存至: {index_file}")
    print(f"   共收錄 {len(char_index)} 個不同的字")
    
    # 顯示可用於同字比對的字
    multi_artist_chars = {char: artists for char, artists in char_index.items() 
                          if len(artists) >= 3}
    if multi_artist_chars:
        print(f"\n可用於「同字異寫比較」的字 ({len(multi_artist_chars)} 個):")
        for char, artists in sorted(multi_artist_chars.items(), 
                                    key=lambda x: len(x[1]), reverse=True)[:20]:
            print(f"  「{char}」: {len(artists)}位 ({', '.join(sorted(artists.keys()))})")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'analyze':
            analyze_labels()
        elif command == 'export':
            export_character_index()
        elif command == 'batch':
            label_images_batch()
        else:
            print("用法：")
            print("  python label_images_simple.py batch    # 批次標註")
            print("  python label_images_simple.py analyze  # 查看統計")
            print("  python label_images_simple.py export   # 導出索引")
    else:
        print("用法：")
        print("  python label_images_simple.py batch    # 批次標註")
        print("  python label_images_simple.py analyze  # 查看統計")
        print("  python label_images_simple.py export   # 導出索引")
