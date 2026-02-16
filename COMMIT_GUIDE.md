# Git Commit 指南

## 📦 要 Commit 的檔案分類

### ✅ 必須 Commit（核心程式碼與配置）

#### 1. 專案結構與配置
```
config.yaml
.gitignore
requirements.txt (如果有更新)
PROJECT_SUMMARY.md
RESTRUCTURE_PLAN.md
COMMIT_GUIDE.md (本檔案)
```

#### 2. 核心程式碼
```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   └── preprocessing/  (整個目錄)
├── analysis/
│   ├── __init__.py
│   ├── similarity_analyzer.py
│   └── restoration_demo.py
├── gui/
│   └── __init__.py
└── utils/
    ├── __init__.py
    ├── config.py
    ├── data_loader.py
```

#### 3. 工具腳本
```
tools/
├── preprocessing/
│   ├── crop_and_denoise.py
│   ├── grid_splitter.py
│   ├── watermark_remover.py
│   ├── full_pipeline.py
│   ├── manual_patcher.py
│   └── README.md
└── analysis/
    └── build_index.py
```

#### 4. 索引檔案（小檔案）
```
data/index/
├── fonts_index.json
└── character_index.json
```

#### 5. 字庫配置與標註
```
Fonts/
├── config.py
├── list.txt
└── my_fonts/csv/
    ├── 00.csv
    ├── 01.csv
    ├── 02.csv
    └── 03.csv
```

---

### ❌ 不要 Commit（大檔案與臨時檔案）

```
# 所有圖片檔案（太大了）
Fonts/**/*.jpg
Fonts/**/*.png
data/**/*.jpg
data/**/*.png

# 備份資料
data/archived/

# 臨時檔案
output/temp/
images/
*.bak
*.tmp

# 虛擬環境
.venv/
venv/

# Claude 工作目錄
.claude/
```

---

## 📝 建議的 Commit Message

### Commit 1: 專案重整與新架構
```bash
git add config.yaml .gitignore PROJECT_SUMMARY.md RESTRUCTURE_PLAN.md COMMIT_GUIDE.md
git add src/ tools/
git add data/index/
git add Fonts/config.py Fonts/list.txt Fonts/my_fonts/csv/

git commit -m "重構專案架構並建立索引系統

主要變更:
- 重新組織目錄結構 (src/, data/, tools/)
- 建立統一配置管理 (config.yaml, src/utils/config.py)
- 實作資料載入器 (src/utils/data_loader.py)
- 整理預處理工具到 tools/preprocessing/
- 建立字庫索引系統 (tools/analysis/build_index.py)

資料統計:
- 4 位書法家: 智永、沈尹默、顏真卿、歐陽詢
- 總圖片數: 2809 張
- 可比對字數: 492 個
- 共有字數: 35 個

功能模組:
- src/core/preprocessing/ - 圖片預處理
- src/analysis/ - 風格分析與相似度計算
- src/utils/ - 配置與資料載入
- tools/preprocessing/ - 5 個預處理工具腳本

索引檔案:
- data/index/fonts_index.json - 字庫總索引
- data/index/character_index.json - 同字索引

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 🚀 執行步驟

### 方法 1: 使用 VSCode Git 面板（推薦）

1. **打開 Source Control 面板** (Ctrl+Shift+G)

2. **Stage 要 commit 的檔案**:
   - 展開 "Changes" 清單
   - **只勾選**以下檔案/資料夾:
     - `config.yaml`
     - `.gitignore`
     - `PROJECT_SUMMARY.md`
     - `RESTRUCTURE_PLAN.md`
     - `COMMIT_GUIDE.md`
     - 整個 `src/` 資料夾
     - 整個 `tools/` 資料夾
     - `data/index/` 資料夾
     - `Fonts/config.py`
     - `Fonts/list.txt`
     - `Fonts/my_fonts/csv/` 資料夾

3. **不要 stage 圖片檔案**:
   - 所有 `.jpg`, `.png` 檔案都不要勾選
   - `data/archived/` 不要勾選
   - `.venv/`, `.claude/` 不要勾選

4. **寫 Commit Message**:
   - 在上方的訊息框貼上上面的 commit message

5. **Commit**:
   - 點擊 "Commit" 按鈕（或按 Ctrl+Enter）

6. **Push**:
   - 點擊 "Sync Changes" 或 "Push"

---

### 方法 2: 使用命令列

```bash
# 1. 先確認狀態
git status

# 2. Stage 核心檔案
git add config.yaml .gitignore PROJECT_SUMMARY.md RESTRUCTURE_PLAN.md COMMIT_GUIDE.md
git add src/ tools/
git add data/index/
git add Fonts/config.py Fonts/list.txt Fonts/my_fonts/csv/

# 3. 確認要 commit 的檔案
git status

# 4. Commit（複製上面的 commit message）
git commit -m "重構專案架構並建立索引系統

主要變更:
- 重新組織目錄結構 (src/, data/, tools/)
- 建立統一配置管理 (config.yaml, src/utils/config.py)
- 實作資料載入器 (src/utils/data_loader.py)
- 整理預處理工具到 tools/preprocessing/
- 建立字庫索引系統 (tools/analysis/build_index.py)

資料統計:
- 4 位書法家: 智永、沈尹默、顏真卿、歐陽詢
- 總圖片數: 2809 張
- 可比對字數: 492 個
- 共有字數: 35 個

功能模組:
- src/core/preprocessing/ - 圖片預處理
- src/analysis/ - 風格分析與相似度計算
- src/utils/ - 配置與資料載入
- tools/preprocessing/ - 5 個預處理工具腳本

索引檔案:
- data/index/fonts_index.json - 字庫總索引
- data/index/character_index.json - 同字索引

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 5. Push
git push origin main
```

---

## ⚠️ 注意事項

1. **不要 commit 圖片檔案**
   - 圖片檔案太大（2809 張）
   - GitHub 有檔案大小限制
   - .gitignore 已經設定好排除規則

2. **確認 .gitignore 生效**
   ```bash
   # 如果 git status 還是顯示很多圖片檔案
   git rm --cached -r Fonts/
   git rm --cached -r data/
   git add .gitignore
   ```

3. **圖片檔案的管理**
   - 圖片保留在本地即可
   - 或使用 Git LFS (Large File Storage)
   - 或上傳到雲端儲存（Google Drive, OneDrive）

4. **未來新增圖片**
   - .gitignore 會自動排除
   - 只有少量範例圖片會被追蹤

---

## 📊 預期結果

Commit 後應該包含約 **50-100 個檔案**，主要是:
- 程式碼檔案 (.py)
- 配置檔案 (.yaml, .json, .csv, .txt)
- 文件檔案 (.md)

**不應該包含**:
- 2809 張圖片檔案
- 虛擬環境檔案
- 臨時檔案

---

## 🔍 檢查清單

在 Push 之前，確認:
- [ ] 只 stage 了程式碼與配置檔案
- [ ] 沒有 stage 圖片檔案
- [ ] Commit message 清楚描述變更
- [ ] .gitignore 已更新

---

完成後，你的 GitHub 專案會有:
✅ 清晰的專案結構
✅ 完整的程式碼
✅ 詳細的文件
✅ 可執行的索引系統

但不會有:
❌ 大量圖片檔案佔用空間
