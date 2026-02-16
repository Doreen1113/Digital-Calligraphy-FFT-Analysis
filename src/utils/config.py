"""配置管理模組"""
import yaml
import os
from pathlib import Path

class Config:
    """全域配置管理器"""

    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        """載入 YAML 配置檔"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置檔不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get(self, *keys, default=None):
        """取得配置值

        例如: config.get('fonts', 'base_dir')
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_calligraphers(self):
        """取得所有書法家資訊"""
        return self.get('fonts', 'calligraphers', default=[])

    def get_font_info(self, font_id):
        """根據 ID 取得書法家資訊"""
        calligraphers = self.get_calligraphers()
        for cal in calligraphers:
            if cal['id'] == font_id:
                return cal
        return None

    def get_index_path(self, index_type):
        """取得索引檔路徑

        Args:
            index_type: 'fonts_index', 'character_index', 'style_features', 'similarity_matrix'
        """
        return self.get('index', index_type)

    def get_fft_params(self):
        """取得 FFT 參數"""
        return self.get('fft', default={})

    def get_output_dir(self, output_type='base_dir'):
        """取得輸出目錄路徑"""
        return self.get('output', output_type)

# 全域配置實例
_config = None

def get_config():
    """取得全域配置實例"""
    global _config
    if _config is None:
        # 尋找專案根目錄的 config.yaml
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent  # src/utils/ -> src/ -> project/
        config_path = project_root / "config.yaml"
        _config = Config(str(config_path))
    return _config
