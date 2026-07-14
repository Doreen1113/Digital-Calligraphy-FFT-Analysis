FROM python:3.11-slim

# 安裝系統依賴（OpenCV headless 需要 libglib2.0；wqy-microhei 提供 CJK 字型給 matplotlib）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 依賴：直接用 requirements.txt，不要維護第二份清單——
# 之前這裡手動列了一份跟 requirements.txt 不同步的套件清單（少了 contrib/ximgproc 需要
# 的骨架化模組），導致 requirements.txt 改了但正式站沒真的裝到新版本，線上一直是舊行為。
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案檔案
COPY . .

# 確保輸出目錄存在
RUN mkdir -p output/comparison output/upload output/temp

# 清除舊的字型快取，讓 matplotlib 下次啟動時重新掃描已安裝的 CJK 字型
RUN python -c "import matplotlib, os, glob; [os.remove(f) for f in glob.glob(os.path.join(matplotlib.get_cachedir(), 'fontlist*'))]"

# 設定 matplotlib 非互動模式
ENV MPLBACKEND=Agg

EXPOSE 8000

CMD ["python", "run_web.py"]
