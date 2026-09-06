"""把 report/report.md 排版成附錄用的 HTML（供 Playwright 轉存 PDF）。

用法：python tools/build_appendix.py
輸出：report/appendix.html
"""
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).parent.parent
SRC = ROOT / "report" / "report.md"
OUT = ROOT / "report" / "appendix.html"

md_text = SRC.read_text(encoding="utf-8")

# 標題行單獨處理成自訂排版，其餘交給 markdown 套件
lines = md_text.split("\n")
title = lines[0].lstrip("# ").strip()
subtitle = lines[1].lstrip("# ").strip()
byline_lines = []
i = 2
while i < len(lines) and lines[i].strip() != "---":
    if lines[i].strip():
        byline_lines.append(lines[i].strip())
    i += 1
body_md = "\n".join(lines[i + 1:])

html_body = markdown.markdown(
    body_md, extensions=["tables", "footnotes", "fenced_code", "sane_lists"]
)
# Markdown 表格內的 <sup> 標記 p 值等上標語法（*text*）已由 markdown 處理，不需額外動作

byline_html = "<br>".join(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", b) for b in byline_lines)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 22mm 20mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Noto Serif", "Times New Roman", "Noto Serif TC", serif;
    font-size: 10.5pt; line-height: 1.55; color: #111; max-width: 100%;
  }}
  .appendix-tag {{
    font-family: "Noto Sans TC", sans-serif; font-size: 9pt; letter-spacing: .12em;
    text-transform: uppercase; color: #8c2f22; text-align: center; margin-bottom: 6mm;
  }}
  h1.title {{ font-size: 16pt; text-align: center; line-height: 1.4; margin-bottom: 2mm; }}
  .subtitle {{ font-size: 12pt; text-align: center; font-style: italic; color: #444; margin-bottom: 4mm; }}
  .byline {{ text-align: center; font-size: 10pt; color: #333; margin-bottom: 8mm; }}
  h2 {{ font-size: 12.5pt; margin: 7mm 0 3mm; border-bottom: 0.6pt solid #999; padding-bottom: 1mm; }}
  h3 {{ font-size: 11pt; margin: 5mm 0 2mm; }}
  p {{ margin: 0 0 3mm; text-align: justify; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 9pt; margin: 3mm 0; }}
  th, td {{ border: 0.5pt solid #999; padding: 1.3mm 2mm; text-align: left; }}
  th {{ background: #f2f2f2; font-weight: 600; }}
  td:not(:first-child), th:not(:first-child) {{ text-align: right; font-variant-numeric: tabular-nums; }}
  strong {{ font-weight: 700; }}
  em {{ font-style: italic; }}
  hr {{ border: none; border-top: 0.4pt solid #ccc; margin: 5mm 0; }}
  a {{ color: #8c2f22; text-decoration: none; }}
  ul {{ margin: 2mm 0 3mm 5mm; padding: 0; }}
  li {{ margin-bottom: 1.3mm; }}
  h2:first-of-type, .abstract-label {{ margin-top: 0; }}
  p.abstract-body {{ font-size: 9.8pt; }}
  code {{ font-family: "Courier New", monospace; font-size: 9pt; background: #f5f5f5; padding: 0 1mm; }}
</style>
</head>
<body>
<div class="appendix-tag">Appendix &middot; Full Technical Report</div>
<h1 class="title">{title}</h1>
<div class="subtitle">{subtitle}</div>
<div class="byline">{byline_html}</div>
{html_body}
</body>
</html>
"""

OUT.write_text(HTML, encoding="utf-8")
print(f"寫入 {OUT}（{len(HTML)} bytes）")
