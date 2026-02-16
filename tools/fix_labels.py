import pandas as pd

def fix_duplicate_labels():
    """修復重複的標籤並重新分析共有字"""
    # 讀取並去重
    df = pd.read_csv('./data/ocr_labels.csv')
    print(f"原始資料行數: {len(df)}")
    
    # 去除重複
    df_clean = df.drop_duplicates()
    print(f"去重後行數: {len(df_clean)}")
    
    # 重新保存
    df_clean.to_csv('./data/ocr_labels_clean.csv', index=False, encoding='utf-8')
    
    # 分析每個書法家的字數
    print("\n📊 各書法家字數統計:")
    artist_counts = df_clean.groupby('artist').size()
    for artist, count in artist_counts.items():
        print(f"   {artist}: {count} 字")
    
    # 分析共有字
    char_artists = {}
    for _, row in df_clean.iterrows():
        char = row['character']
        artist = row['artist']
        if char not in char_artists:
            char_artists[char] = set()
        char_artists[char].add(artist)
    
    # 找出所有書法家都有的字
    num_artists = len(df_clean['artist'].unique())
    print(f"\n總書法家數: {num_artists}")
    
    # 按書法家數量分組
    for min_artists in [6, 5, 4, 3]:
        common_chars = [char for char, artists in char_artists.items() 
                       if len(artists) >= min_artists and char != '?']
        print(f"\n🎯 {min_artists}個書法家共有: {len(common_chars)} 字")
        if common_chars and len(common_chars) <= 50:
            print(f"   {''.join(sorted(common_chars))}")
        elif common_chars:
            print(f"   {' '.join(sorted(common_chars)[:30])}...")
    
    # 詳細分析每個字的書法家分佈
    print(f"\n📋 字頻統計 (前30個):")
    char_counts = {}
    for char, artists in char_artists.items():
        char_counts[char] = len(artists)
    
    sorted_chars = sorted(char_counts.items(), key=lambda x: x[1], reverse=True)
    for i, (char, count) in enumerate(sorted_chars[:30]):
        artists_list = sorted(list(char_artists[char]))
        print(f"   {char}: {count}人 ({', '.join(artists_list)})")

if __name__ == "__main__":
    fix_duplicate_labels()