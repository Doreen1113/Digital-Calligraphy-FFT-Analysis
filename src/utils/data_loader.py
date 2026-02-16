"""統一的資料載入器"""
import os
import pandas as pd
import cv2
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from .config import get_config

class FontDataLoader:
    """字庫資料載入器"""

    def __init__(self):
        self.config = get_config()
        self.calligraphers = self.config.get_calligraphers()

    def get_calligrapher_list(self) -> List[str]:
        """取得所有書法家名稱列表"""
        return [cal['name'] for cal in self.calligraphers]

    def get_calligrapher_info(self, name: str) -> Optional[Dict]:
        """根據名稱取得書法家資訊"""
        for cal in self.calligraphers:
            if cal['name'] == name:
                return cal
        return None

    def load_labels(self, calligrapher_name: str) -> pd.DataFrame:
        """載入指定書法家的標註檔

        Args:
            calligrapher_name: 書法家名稱（如 "智永"）

        Returns:
            pandas DataFrame with columns: filename, character, confidence
        """
        info = self.get_calligrapher_info(calligrapher_name)
        if not info:
            raise ValueError(f"找不到書法家: {calligrapher_name}")

        labels_file = info['labels_file']
        if not os.path.exists(labels_file):
            raise FileNotFoundError(f"標註檔不存在: {labels_file}")

        df = pd.read_csv(labels_file)
        return df

    def load_image(self, calligrapher_name: str, filename: str) -> Optional[any]:
        """載入指定書法家的單張圖片

        Args:
            calligrapher_name: 書法家名稱
            filename: 圖片檔名

        Returns:
            OpenCV 圖片物件 (BGR)
        """
        info = self.get_calligrapher_info(calligrapher_name)
        if not info:
            return None

        image_path = os.path.join(info['image_dir'], filename)
        if not os.path.exists(image_path):
            return None

        return cv2.imread(image_path)

    def get_image_path(self, calligrapher_name: str, filename: str) -> str:
        """取得圖片的完整路徑"""
        info = self.get_calligrapher_info(calligrapher_name)
        if not info:
            return ""
        return os.path.join(info['image_dir'], filename)

    def get_all_characters(self, calligrapher_name: str) -> List[Tuple[str, str]]:
        """取得指定書法家的所有字元

        Returns:
            List of (filename, character) tuples
        """
        df = self.load_labels(calligrapher_name)
        return list(zip(df['filename'], df['character']))

    def get_character_image_path(self, calligrapher_name: str, character: str) -> Optional[str]:
        """根據字元取得圖片路徑（只返回第一個匹配）

        Args:
            calligrapher_name: 書法家名稱
            character: 要查詢的字

        Returns:
            圖片完整路徑，若不存在則返回 None
        """
        df = self.load_labels(calligrapher_name)
        matches = df[df['character'] == character]

        if matches.empty:
            return None

        filename = matches.iloc[0]['filename']
        return self.get_image_path(calligrapher_name, filename)

    def get_all_character_images(self, calligrapher_name: str, character: str) -> List[str]:
        """取得指定字的所有圖片路徑（可能有多個）"""
        df = self.load_labels(calligrapher_name)
        matches = df[df['character'] == character]

        if matches.empty:
            return []

        info = self.get_calligrapher_info(calligrapher_name)
        image_dir = info['image_dir']

        return [os.path.join(image_dir, filename) for filename in matches['filename']]

    def get_statistics(self, calligrapher_name: str) -> Dict:
        """取得字庫統計資訊"""
        df = self.load_labels(calligrapher_name)
        info = self.get_calligrapher_info(calligrapher_name)

        return {
            'name': calligrapher_name,
            'dynasty': info['dynasty'],
            'style': info['style'],
            'total_images': len(df),
            'unique_characters': df['character'].nunique(),
            'avg_confidence': df['confidence'].mean() if 'confidence' in df.columns else None
        }

    def get_all_statistics(self) -> List[Dict]:
        """取得所有書法家的統計資訊"""
        stats = []
        for cal in self.calligraphers:
            try:
                stat = self.get_statistics(cal['name'])
                stats.append(stat)
            except Exception as e:
                print(f"⚠️  無法載入 {cal['name']} 的資料: {e}")
        return stats
