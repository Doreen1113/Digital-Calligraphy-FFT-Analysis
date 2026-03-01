"""
書法風格分析系統 - Web 啟動腳本
啟動 FastAPI 伺服器，在瀏覽器中使用書法分析功能

使用方式：
    python run_web.py
    然後在瀏覽器開啟 http://localhost:8002
"""
import os
import sys

# 確保工作目錄為專案根目錄
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設定 matplotlib 為非互動模式（必須在任何 matplotlib import 之前）
import matplotlib
matplotlib.use('Agg')


def main():
    """啟動 Web 伺服器"""
    # 檢查所有必要的依賴
    required_modules = ['fastapi', 'uvicorn', 'jinja2']
    missing = []

    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)

    if missing:
        print("[Error] 缺少 Web 伺服器依賴: " + ", ".join(missing))
        print("請執行: pip install fastapi uvicorn[standard] jinja2 python-multipart")
        sys.exit(1)

    try:
        import uvicorn
    except ImportError:
        print("[Error] 無法載入 uvicorn")
        sys.exit(1)

    print("=" * 60)
    print("  書法風格分析系統 - Web 版")
    print("=" * 60)
    print()
    print("  啟動伺服器中...")
    print("  開啟瀏覽器訪問: http://localhost:8002")
    print("  按 Ctrl+C 停止伺服器")
    print()
    print("=" * 60)

    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    reload = not os.environ.get("PORT")  # 雲端部署時關閉 reload

    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
