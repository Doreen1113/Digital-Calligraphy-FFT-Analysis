# 專案重整執行計劃

## Phase 1: 建立新目錄結構
- [x] 建立 src/ 核心程式碼目錄
- [x] 建立 data/ 統一資料目錄
- [x] 建立 tools/preprocessing/ 預處理工具目錄
- [x] 建立 docs/ 文件目錄

## Phase 2: 移動核心程式碼
- [ ] core/fft.py → src/core/fft.py
- [ ] core/SVG.py → src/core/svg.py
- [ ] core/GUI.py → src/gui/main_window.py
- [ ] Preprocessing/ → src/core/preprocessing/
- [ ] modules/similarity_analyzer.py → src/analysis/similarity.py
- [ ] modules/restoration_demo.py → src/analysis/restoration_demo.py

## Phase 3: 整理預處理工具
- [ ] test.py → tools/preprocessing/crop_and_denoise.py
- [ ] test1.py → tools/preprocessing/grid_splitter.py
- [ ] test2.py → tools/preprocessing/watermark_remover.py
- [ ] test3.py → tools/preprocessing/full_pipeline.py
- [ ] insert.py → tools/preprocessing/manual_patcher.py

## Phase 4: 整理資料目錄
- [ ] Fonts/my_fonts/00 → data/fonts/00_智永/
- [ ] Fonts/my_fonts/01 → data/fonts/01_沈尹默/
- [ ] Fonts/my_fonts/02 → data/fonts/02_顏真卿/
- [ ] Fonts/my_fonts/03 → data/fonts/03_歐陽詢/
- [ ] Fonts/my_fonts/csv/*.csv → 各字庫目錄下的 labels.csv
- [ ] data/ (舊Kaggle) → data/archived/kaggle/

## Phase 5: 清理
- [ ] 刪除空目錄
- [ ] 更新 .gitignore
- [ ] 建立新的 main.py 入口
