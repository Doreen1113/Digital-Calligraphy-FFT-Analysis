"""求字生成服務（在 fontdiff conda 環境執行，port 8135）。

GET /generate?char=齋&cal=yan_zhenqing[&k=5]
  → 以 FontDiffuser（本資料集 fine-tune 15k 步，guidance 12）生成該書法家風格的字。
    生成 k 個候選（不同風格參考圖），由獨立訓練的選擇器（selector_classifier.pth）
    挑出最像目標書法家者，回傳 base64 PNG 與信心度。
GET /health
"""
from __future__ import annotations

import base64
import io
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException, Query
from PIL import Image, ImageDraw, ImageFont
from torchvision import transforms
from torchvision.models import resnet18

FD = Path(__file__).parent
CALLI = Path("/home/intern_2603055/projects/tuijian/Digital-Calligraphy-FFT-Analysis")
CKPT = FD / "outputs" / "calli_finetune" / "global_step_15000"
SELECTOR = CALLI / "experiments" / "cache" / "selector_classifier.pth"
KAIU_DIR = CALLI / "data" / "paired" / "source"          # 訓練用的標楷體渲染（1,057 字）
EDUKAI = Path("/home/intern_2603055/projects/tuijian/fonts/edukai/edukai-5.0.ttf")
GUIDANCE = 12.0

sys.path.insert(0, str(FD))
sys.path.insert(0, str(CALLI / "experiments"))
from features import binarize  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

LABELS = ["liu_gongquan", "ouyang_xun", "shen_yinmo", "yan_zhenqing",
          "yu_shinan", "zhao_mengfu", "zhiyong"]          # 與訓練協定相同的字母序
DEV = "cuda:0"

app = FastAPI(title="墨跡求字生成服務")
_state: dict = {}
_cache: dict = {}   # (char, cal, k, seed) → 回應；同一句話重生成秒回


def _load():
    _argv = sys.argv
    sys.argv = [sys.argv[0]]
    import sample as fd_sample
    fd_args = fd_sample.arg_parse()
    sys.argv = _argv
    fd_args.ckpt_dir = str(CKPT)
    fd_args.demo = True
    fd_args.save_image = False
    fd_args.character_input = False
    fd_args.algorithm_type = "dpmsolver++"
    fd_args.guidance_type = "classifier-free"
    fd_args.guidance_scale = GUIDANCE
    fd_args.num_inference_steps = 20
    fd_args.method = "multistep"
    fd_args.device = DEV
    _state["fd"] = fd_sample
    _state["args"] = fd_args
    _state["pipe"] = fd_sample.load_fontdiffuer_pipeline(fd_args)

    sel = resnet18()
    sel.fc = nn.Linear(sel.fc.in_features, 7)
    sel.load_state_dict(torch.load(SELECTOR, map_location=DEV))
    _state["selector"] = sel.to(DEV).eval()
    _state["tf"] = transforms.Compose([transforms.ToTensor(),
                                       transforms.Normalize([0.5] * 3, [0.5] * 3)])

    m = pd.read_csv(CALLI / "experiments" / "manifest.csv")
    _state["by_label"] = {l: g["path"].tolist() for l, g in m.groupby("label")}
    _state["written"] = {l: set(g["char"]) for l, g in m.groupby("label")}
    _state["font"] = ImageFont.truetype(str(EDUKAI), 200)
    # PIL 對字型沒有的字仍會畫出一個非空的佔位符方塊（tofu），
    # 不能用「畫出來的寬高是否為 0」判斷是否支援——必須直接查字型的 cmap 表。
    _tt = TTFont(str(EDUKAI))
    _state["font_cmap"] = set(_tt.getBestCmap().keys())
    print("gen_server ready", flush=True)


@app.on_event("startup")
def _startup():
    _load()


def content_image(char: str) -> tuple[Image.Image, str]:
    """優先用訓練時的標楷體渲染；不在字庫的字改用教育部標準楷書現渲染。"""
    p = KAIU_DIR / f"{ord(char):05X}.png"
    if p.exists():
        return Image.open(p).convert("RGB"), "kaiu"
    if ord(char) not in _state["font_cmap"]:
        raise HTTPException(400, f"「{char}」過於罕見，教育部標準楷書字型未收錄此字，暫時無法生成")
    img = Image.new("L", (256, 256), 255)
    d = ImageDraw.Draw(img)
    f = _state["font"]
    bb = d.textbbox((0, 0), char, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((256 - w) // 2 - bb[0], (256 - h) // 2 - bb[1]), char, fill=0, font=f)
    return img.convert("RGB"), "edukai"


def selector_scores(pil: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """回傳 (logits, 溫度軟化後的機率)。排序用 logit——softmax 在生成圖上會飽和成 0/1，
    五個候選分數全相同，重排就失效。"""
    arr = np.array(pil.convert("L"))
    ink = cv2.resize(binarize(arr), (224, 224), interpolation=cv2.INTER_AREA)
    x = _state["tf"](np.stack([ink] * 3, -1)).unsqueeze(0).to(DEV)
    with torch.no_grad():
        logits = _state["selector"](x)[0]
        return logits.cpu().numpy(), torch.softmax(logits / 4.0, 0).cpu().numpy()


def to_b64(pil: Image.Image, clean: bool = True) -> str:
    if clean:
        ink = binarize(np.array(pil.convert("L")))          # 緊貼邊框的 256×256
        canvas = np.zeros((320, 320), np.uint8)             # 留 10% 白邊再縮回 256
        canvas[32:288, 32:288] = ink
        pil = Image.fromarray(255 - cv2.resize(canvas, (256, 256), interpolation=cv2.INTER_AREA))
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@app.get("/health")
def health():
    return {"ok": "pipe" in _state, "ckpt": str(CKPT), "guidance": GUIDANCE}


@app.get("/generate")
def generate(char: str = Query(..., min_length=1, max_length=1),
             cal: str = Query(...),
             k: int = Query(5, ge=1, le=8),
             seed: int | None = None):
    if cal not in LABELS:
        raise HTTPException(400, f"cal 必須是 {LABELS}")
    key = (char, cal, k, seed)
    if key in _cache:
        return _cache[key]
    rng = random.Random(seed)
    content, content_src = content_image(char)
    refs = rng.sample(_state["by_label"][cal], k)
    ti = LABELS.index(cal)

    cands = []
    for ref in refs:
        style = Image.open(CALLI / ref).convert("RGB")
        out = _state["fd"].sampling(_state["args"], _state["pipe"],
                                    content_image=content, style_image=style)
        logits, p = selector_scores(out)
        cands.append({"img": out, "ref": ref, "logit": float(logits[ti]),
                      "score": float(p[ti]), "pred": LABELS[int(logits.argmax())]})
    cands.sort(key=lambda c: -c["logit"])
    best = cands[0]
    result = {
        "char": char, "cal": cal,
        "already_written": char in _state["written"][cal],
        "content_source": content_src,
        "best": {"png": to_b64(best["img"]), "score": best["score"],
                 "ref": best["ref"], "pred": best["pred"]},
        "candidates": [{"png": to_b64(c["img"]), "score": c["score"], "pred": c["pred"]}
                       for c in cands],
        "content_png": to_b64(content, clean=False),
    }
    if len(_cache) > 2000:
        _cache.clear()
    _cache[key] = result
    return result
