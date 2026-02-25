# fonts/config.py
"""字庫配置中心"""

# === Kaggle 舊資料集（6位書法家）===
KAGGLE_FONTS = {
    'base_dir': './fonts/kaggle_dataset',
    'artists': ['Cu_Suiliang', 'Liu_Gongquan', 'Ou_Yangxun', 
                'Wen_Zhengmeng', 'Yan_Zhenqing', 'Zhao_Mengfu'],
    'labels_file': './fonts/kaggle_dataset/labels.csv'
}

# === 你的新字庫（4組）===
MY_FONTS = {
    'base_dir': './fonts/my_fonts',
    'fonts': {
        '00': {
            'name': '智永',
            'chars_dir': './fonts/my_fonts/00_qianziwen/chars',
            'labels_file': './fonts/my_fonts/00_qianziwen/labels.csv',
            'text_source': './fonts/00.txt'  # 已知文字順序
        },
        '01': {
            'name': '沈尹默',
            'chars_dir': './fonts/my_fonts/01_unknown/chars',
            'labels_file': './fonts/my_fonts/01_unknown/labels.csv',
            'needs_ocr': True
        },
        '02': {
            'name': '歐陽詢',
            'chars_dir': './fonts/my_fonts/02_grid_style/chars',
            'labels_file': './fonts/my_fonts/02_grid_style/labels.csv',
            'needs_ocr': True
        },
        '03': {
            'name': '柳公權',
            'chars_dir': './fonts/my_fonts/03_mixed_style/chars',
            'labels_file': './fonts/my_fonts/03_mixed_style/labels.csv',
            'needs_ocr': True
        },
        '04': {
            'name': '趙孟頫',
            'chars_dir': './fonts/my_fonts/04_mixed_style/chars',
            'labels_file': './fonts/my_fonts/04_mixed_style/labels.csv',
            'needs_ocr': './fonts/04.txt'
        }
    }
}

def get_all_font_dirs(use_kaggle=False, use_my=True):
    """獲取要分析的所有字庫"""
    dirs = []
    if use_kaggle:
        for artist in KAGGLE_FONTS['artists']:
            dirs.append({
                'name': artist,
                'path': f"{KAGGLE_FONTS['base_dir']}/{artist}",
                'labels': KAGGLE_FONTS['labels_file']
            })
    
    if use_my:
        for font_id, info in MY_FONTS['fonts'].items():
            dirs.append({
                'name': info['name'],
                'path': info['chars_dir'],
                'labels': info['labels_file']
            })
    
    return dirs