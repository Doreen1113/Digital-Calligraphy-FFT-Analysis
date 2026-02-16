#!/bin/bash
# 快速 Commit 腳本

echo "🚀 準備 Commit..."

# Stage 核心檔案
git add config.yaml .gitignore PROJECT_SUMMARY.md RESTRUCTURE_PLAN.md COMMIT_GUIDE.md QUICK_COMMIT.sh
git add src/ tools/
git add data/index/
git add Fonts/config.py Fonts/list.txt Fonts/my_fonts/csv/

echo "✅ 已 Stage 以下檔案:"
git status --short | grep "^A"

echo ""
echo "📊 檔案統計:"
git status --short | grep "^A" | wc -l
echo "個檔案已準備 Commit"

echo ""
echo "📝 建議的 Commit Message (複製下方內容):"
echo "=========================================="
cat << 'EOF'
重構專案架構並建立索引系統

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

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
echo "=========================================="

echo ""
echo "⚡ 接下來請執行:"
echo "  1. 在 VSCode 檢查 Source Control 面板的變更"
echo "  2. 複製上方的 Commit Message"
echo "  3. 在 VSCode Commit"
echo "  4. Push 到 GitHub"
echo ""
echo "或者直接執行:"
echo "  git commit -F COMMIT_MESSAGE.txt"
echo "  git push origin main"
