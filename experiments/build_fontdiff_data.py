"""把完整資料集（manifest.csv, 7,449 張）轉成 FontDiffuser 訓練格式。

輸出到 FontDiffuser/data_calli/train/：
  ContentImage/{char}.jpg                 ← 標楷體（data/paired/source，1,057 字全有）
  TargetImage/{label}/{label}+{char}.jpg  ← 書法真跡（同一書法家多本字帖合併）

排除 generation_manifest.csv 用過的 (cal_book, hex) 字，保留當 fine-tune 後評估集。
同一書法家同一字多張取第一張。
"""
from pathlib import Path

import pandas as pd
from PIL import Image

CALLI = Path(__file__).parent.parent
OUT = Path("/home/intern_2603055/projects/tuijian/FontDiffuser/data_calli/train")

BOOK2LABEL = {"zhiyong_00": "zhiyong", "ouyang_xun_03": "ouyang_xun",
              "yu_shinan_06": "yu_shinan", "yan_zhenqing_07": "yan_zhenqing",
              "liu_gongquan_02": "liu_gongquan", "zhao_mengfu_04": "zhao_mengfu",
              "shen_yinmo_01": "shen_yinmo"}

gm = pd.read_csv(CALLI / "experiments" / "generated" / "generation_manifest.csv")
held_out = {(BOOK2LABEL[c], chr(int(h, 16))) for c, h in zip(gm["cal"], gm["hex"])}

manifest = pd.read_csv(CALLI / "experiments" / "manifest.csv")
src_dir = CALLI / "data" / "paired" / "source"

(OUT / "ContentImage").mkdir(parents=True, exist_ok=True)
content_written = set()
n_target = n_skip = 0
seen = set()

for _, r in manifest.iterrows():
    label, char = r["label"], r["char"]
    if (label, char) in held_out:
        n_skip += 1
        continue
    if (label, char) in seen:
        continue
    hexname = f"{ord(char):05X}.png"
    src = src_dir / hexname
    if not src.exists():
        continue
    seen.add((label, char))
    d = OUT / "TargetImage" / label
    d.mkdir(parents=True, exist_ok=True)
    Image.open(CALLI / r["path"]).convert("RGB").save(d / f"{label}+{char}.jpg")
    n_target += 1
    if char not in content_written:
        Image.open(src).convert("RGB").save(OUT / "ContentImage" / f"{char}.jpg")
        content_written.add(char)

print(f"content {len(content_written)}，target {n_target}，held-out 排除 {n_skip}")
for d in sorted((OUT / "TargetImage").iterdir()):
    print(f"  {d.name:15s} {len(list(d.glob('*.jpg')))}")
