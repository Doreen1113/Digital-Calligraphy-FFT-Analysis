"""建立分類實驗的資料清單 manifest.csv。

從 data/paired/target/{calligrapher}/{unicodehex}_{orig}.png 蒐集樣本，
每列記錄：書法家 ID、書法家（合併同一人多本字帖）、字元、圖片路徑。
沈尹默的 4 本字帖（01/08/09/10）合併為同一類別。
"""
import csv
from pathlib import Path

ROOT = Path(__file__).parent.parent
TARGET = ROOT / "data" / "paired" / "target"
OUT = Path(__file__).parent / "manifest.csv"

# 資料夾名 → 類別（同一書法家的多本字帖合併）
MERGE = {
    "zhiyong_00": "zhiyong",
    "shen_yinmo_01": "shen_yinmo",
    "shen_yinmo_08": "shen_yinmo",
    "shen_yinmo_09": "shen_yinmo",
    "shen_yinmo_10": "shen_yinmo",
    "liu_gongquan_02": "liu_gongquan",
    "ouyang_xun_03": "ouyang_xun",
    "zhao_mengfu_04": "zhao_mengfu",
    "yu_shinan_06": "yu_shinan",
    "yan_zhenqing_07": "yan_zhenqing",
}

import json

idx = json.loads((ROOT / "data" / "index" / "character_index.json").read_text(encoding="utf-8"))
rows, missing = [], 0
for char, cals in idx["character_map"].items():
    for book, instances in cals.items():
        if book not in MERGE:
            continue
        for inst in instances:
            raw = inst.get("image_path", "").replace("\\", "/")
            rel = raw.split("Fonts/my_fonts/")[-1] if "Fonts/my_fonts/" in raw else None
            p = ROOT / "Fonts" / "my_fonts" / rel if rel else None
            if p is None or not p.exists():
                # 索引存的是舊路徑格式，退而求其次用 font_id + filename 組
                fid, fn = inst.get("font_id"), inst.get("filename")
                p = ROOT / "Fonts" / "my_fonts" / str(fid) / str(fn) if fid and fn else None
            if p is None or not p.exists():
                missing += 1
                continue
            rows.append({"book": book, "label": MERGE[book], "char": char,
                         "path": str(p.relative_to(ROOT))})
print(f"索引中找不到實際圖檔: {missing}")

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["book", "label", "char", "path"])
    w.writeheader()
    w.writerows(rows)

from collections import Counter
by_label = Counter(r["label"] for r in rows)
chars_by_label = {}
for r in rows:
    chars_by_label.setdefault(r["label"], set()).add(r["char"])
print(f"總樣本 {len(rows)}，類別 {len(by_label)}")
for k in sorted(by_label):
    print(f"  {k:15s} {by_label[k]:5d} 張 / {len(chars_by_label[k]):4d} 個獨特字")
all_chars = set.union(*chars_by_label.values())
common = set.intersection(*chars_by_label.values())
print(f"全部獨特字 {len(all_chars)}，7 人共同字 {len(common)}")
