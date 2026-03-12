FROM python:3.11-slim

# 安裝系統依賴（OpenCV headless 需要 libglib2.0；wqy-microhei 提供 CJK 字型給 matplotlib）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 依賴
# 使用 headless 版 OpenCV（不需要 GUI 依賴）
RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    matplotlib \
    pandas \
    scipy \
    seaborn \
    pyyaml \
    pypinyin \
    "Pillow>=10.0.0" \
    fastapi \
    "uvicorn[standard]" \
    jinja2 \
    python-multipart

# 複製專案檔案
COPY . .

# 確保輸出目錄存在
RUN mkdir -p output/comparison output/upload output/temp

# 重建 matplotlib 字型快取（讓新安裝的 CJK 字型被識別）
RUN python -c "import matplotlib.font_manager as fm; fm._rebuild()"

# 設定 matplotlib 非互動模式
ENV MPLBACKEND=Agg

EXPOSE 8000

CMD ["python", "run_web.py"]
