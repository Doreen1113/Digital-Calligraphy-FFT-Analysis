"""實驗五：風格生成 + 同字真跡量化評估（在 fontdiff conda 環境執行）。

流程：
1. 每位書法家抽 30 個「有真跡 ground truth」的字。
2. FontDiffuser zero-shot：content=標楷體標準字、style=該書法家的另一個字。
3. 與真跡評估：
   - SSIM（生成 vs 真跡，二值化置中後）
   - 風格分類器判定：載入 experiments 訓練協定的 ResNet-18
     看生成的字被判為目標書法家的比例（style match rate）
   - 對照組：真跡本身的 style match rate（上限）與標楷體 content 圖（下限）

用法（在 FontDiffuser 目錄、fontdiff 環境）：
  python /path/to/experiments/run_generation.py
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

CALLI = Path("/home/intern_2603055/projects/tuijian/Digital-Calligraphy-FFT-Analysis")
FD = Path("/home/intern_2603055/projects/tuijian/FontDiffuser")
OUT = CALLI / "experiments" / "generated"
sys.path.insert(0, str(FD))
sys.path.insert(0, str(CALLI / "experiments"))

CALS = ["zhiyong_00", "ouyang_xun_03", "yu_shinan_06", "yan_zhenqing_07",
        "liu_gongquan_02", "zhao_mengfu_04", "shen_yinmo_01"]
N_PER_CAL = 30


def collect_tasks(rng: random.Random):
    """回傳 [(cal, hex, content_path, style_path, gt_path), ...]"""
    tasks = []
    src_dir = CALLI / "data" / "paired" / "source"
    for cal in CALS:
        tgt_dir = CALLI / "data" / "paired" / "target" / cal
        by_hex = {}
        for p in tgt_dir.glob("*.png"):
            by_hex.setdefault(p.stem.split("_")[0], []).append(p)
        usable = [h for h in by_hex if (src_dir / f"{h}.png").exists()]
        rng.shuffle(usable)
        chosen = usable[:N_PER_CAL]
        for h in chosen:
            gt = by_hex[h][0]
            style_hex = rng.choice([x for x in usable if x != h])
            style = by_hex[style_hex][0]
            tasks.append((cal, h, src_dir / f"{h}.png", style, gt))
    return tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ckpt_dir", default=str(FD / "ckpt"),
                    help="模型權重目錄（可指向 fine-tune 的 checkpoint）")
    ap.add_argument("--out", default=str(OUT), help="生成輸出目錄")
    ap.add_argument("--guidance_scale", type=float, default=7.5)
    ap.add_argument("--n_candidates", type=int, default=1,
                    help="每個字生成幾個候選（不同風格參考圖），供事後重排選優")
    args_cli = ap.parse_args()
    rng = random.Random(args_cli.seed)
    out_dir = Path(args_cli.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── FontDiffuser pipeline（載入一次）──
    # fd_sample.arg_parse() 會解析 sys.argv，我們自己的參數會讓它罷工，先清空
    import sys as _sys
    _argv_backup = _sys.argv
    _sys.argv = [_sys.argv[0]]
    import sample as fd_sample
    fd_args = fd_sample.arg_parse()
    _sys.argv = _argv_backup
    fd_args.ckpt_dir = args_cli.ckpt_dir
    fd_args.demo = True
    fd_args.save_image = False
    fd_args.character_input = False
    fd_args.algorithm_type = "dpmsolver++"
    fd_args.guidance_type = "classifier-free"
    fd_args.guidance_scale = args_cli.guidance_scale
    fd_args.num_inference_steps = 20
    fd_args.method = "multistep"
    fd_args.device = "cuda:0"
    pipe = fd_sample.load_fontdiffuer_pipeline(fd_args)

    tasks = collect_tasks(rng)
    print(f"共 {len(tasks)} 個生成任務", flush=True)
    rows = []
    for i, (cal, h, content_p, style_p, gt_p) in enumerate(tasks):
        content = Image.open(content_p).convert("RGB")
        # 候選 0 用原本的 style ref（與 K=1 完全一致）；其餘候選換不同參考圖
        cal_dir = style_p.parent
        pool = [p for p in cal_dir.glob("*.png") if p.stem.split("_")[0] != h]
        for c in range(args_cli.n_candidates):
            sp = style_p if c == 0 else Path(rng.choice(pool))
            style = Image.open(sp).convert("RGB")
            out_img = fd_sample.sampling(fd_args, pipe, content_image=content, style_image=style)
            suffix = "" if args_cli.n_candidates == 1 else f"__cand{c}"
            out_path = out_dir / f"{cal}__{h}{suffix}.png"
            out_img.save(out_path)
            rows.append((cal, h, str(out_path), str(gt_p), str(content_p), str(sp)))
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(tasks)}", flush=True)

    import csv
    with open(out_dir / "generation_manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cal", "hex", "gen", "gt", "content", "style"])
        w.writerows(rows)
    print("生成完畢 →", out_dir, flush=True)


if __name__ == "__main__":
    main()
