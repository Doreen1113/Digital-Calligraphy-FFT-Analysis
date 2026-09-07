"""合成 project page 用的集字示範動畫（GIF）。

畫面內容：一句話逐字在宣紙上組成，每個字標明來源
（綠＝該書法家真跡；紅＝字帖沒有、由模型補字），最後整幅停留。

直接呼叫本機平台 API 取圖，不錄螢幕，因此沒有瀏覽器外框、節奏可控。
用法：python tools/build_hero_anim.py
"""
from __future__ import annotations

import argparse
import base64
import json
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

API = "http://127.0.0.1:8123/api/generate/char"
HOST = "http://127.0.0.1:8123"
FONT = "/home/intern_2603055/projects/tuijian/fonts/edukai/edukai-5.0.ttf"

PHRASE, CAL = "寧靜致遠", "趙孟頫"
CELL, GAP, PAD = 190, 16, 40
PAPER = (250, 246, 240)
INK = (34, 30, 28)
REAL_C = (31, 122, 77)
AI_C = (160, 61, 44)
MUTED = (140, 132, 124)


def fetch(char: str, name: str) -> tuple[Image.Image, str]:
    q = urllib.parse.urlencode({"char": char, "name": name, "k": 1})
    with urllib.request.urlopen(f"{API}?{q}", timeout=180) as r:
        j = json.loads(r.read().decode())
    src = j["source"]
    if src == "real":
        url = j["real_glyphs"][0]
    elif src == "cache":
        url = j["best"]["url"]
    else:
        img = Image.open(BytesIO(base64.b64decode(j["best"]["png"])))
        return img.convert("L"), "ai"
    with urllib.request.urlopen(HOST + url, timeout=60) as r:
        return Image.open(BytesIO(r.read())).convert("L"), src


def compose(glyphs, sources, upto: int, title_font, label_font) -> Image.Image:
    """畫出前 upto 個字已完成的狀態（橫式，適合當寬版 hero）。"""
    n = len(glyphs)
    W = n * CELL + (n - 1) * GAP + PAD * 2
    H = CELL + PAD * 2 + 96
    canvas = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(canvas)

    # 教育部楷書沒有「・」，用空白分隔避免出現豆腐字
    d.text((PAD, 26), f"{PHRASE}　{CAL}", font=title_font, fill=INK)

    for i in range(n):
        x = PAD + i * (CELL + GAP)
        y = PAD + 62
        d.rectangle([x, y, x + CELL, y + CELL], outline=(228, 221, 211), width=1)
        if i < upto:
            canvas.paste(glyphs[i].convert("RGB"), (x, y))
            is_real = sources[i] == "real"
            c = REAL_C if is_real else AI_C
            txt = "真跡" if is_real else "AI 補字"
            tw = d.textlength(txt, font=label_font)
            d.text((x + (CELL - tw) / 2, y + CELL + 12), txt, font=label_font, fill=c)
    return canvas


def main(out: Path):
    title_font = ImageFont.truetype(FONT, 30)
    label_font = ImageFont.truetype(FONT, 24)

    glyphs, sources = [], []
    for ch in PHRASE:
        im, src = fetch(ch, CAL)
        glyphs.append(im.resize((CELL, CELL), Image.LANCZOS))
        sources.append(src)
    n_real = sources.count("real")
    print(f"{PHRASE}×{CAL}：真跡 {n_real}、補字 {len(sources) - n_real}")

    frames, durations = [], []
    frames.append(compose(glyphs, sources, 0, title_font, label_font)); durations.append(600)
    for i in range(1, len(glyphs) + 1):
        frames.append(compose(glyphs, sources, i, title_font, label_font))
        durations.append(700)
    frames.append(frames[-1]); durations.append(2600)      # 完成後停留

    out.parent.mkdir(parents=True, exist_ok=True)
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=96) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:],
                duration=durations, loop=0, optimize=True, disposal=2)
    print(f"完成：{len(frames)} 幀 → {out}（{out.stat().st_size/1e6:.2f} MB）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/img/hero_jizi.gif")
    main(Path(ap.parse_args().out))
