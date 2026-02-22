"""
書法 FFT 分析系統 - GUI 啟動腳本
"""
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(__file__))

# 檢查 Tkinter 是否可用
try:
    import tkinter
except ImportError:
    print("[Error] Tkinter 未安裝")
    print("請安裝 Tkinter:")
    print("  - Windows: Python 安裝時通常已包含")
    print("  - Linux: sudo apt-get install python3-tk")
    print("  - Mac: brew install python-tk")
    sys.exit(1)

# 啟動 GUI
from gui.main_window import main

if __name__ == "__main__":
    main()
