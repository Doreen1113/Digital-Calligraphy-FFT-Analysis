"""產生求字頁的示範作品（直書、宣紙底、含來源標記）。

輸出 web/static/img/showcase/{slug}.png ＋ showcase.json
用法：python tools/build_showcase.py
"""
import json
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent.parent
OUT = ROOT / "web" / "static" / "img" / "showcase"
API = "http://127.0.0.1:8123/api/generate/char"

PIECES = [
    ("shangshan", "上善若水", "顏真卿"),
    ("ningjing", "寧靜致遠", "趙孟頫"),
    ("houde", "厚德載物", "柳公權"),
    ("wenguzhixin", "溫故知新", "智永"),
]

CELL, GAP, PAD = 190, 14, 34
PAPER = (251, 248, 241)


def fetch(char: str, name: str) -> tuple[Image.Image, str]:
    q = urllib.parse.urlencode({"char": char, "name": name, "k": 5})  # 示範作品維持高品質重排
    with urllib.request.urlopen(f"{API}?{q}", timeout=180) as r:
        j = json.loads(r.read().decode())
    src = j["source"]
    if src == "real":
        url = j["real_glyphs"][0]
    elif src == "cache":
        url = j["best"]["url"]
    else:
        import base64
        return Image.open(BytesIO(base64.b64decode(j["best"]["png"]))).convert("L"), "ai"
    with urllib.request.urlopen("http://127.0.0.1:8123" + url, timeout=60) as r:
        return Image.open(BytesIO(r.read())).convert("L"), src


def compose(chars: str, name: str) -> tuple[Image.Image, list[str]]:
    glyphs, sources = [], []
    for ch in chars:
        im, src = fetch(ch, name)
        glyphs.append(im.resize((CELL, CELL), Image.LANCZOS))
        sources.append(src)

    W = CELL + PAD * 2
    H = len(glyphs) * CELL + (len(glyphs) - 1) * GAP + PAD * 2
    canvas = Image.new("RGB", (W, H), PAPER)
    for i, g in enumerate(glyphs):
        canvas.paste(g.convert("RGB"), (PAD, PAD + i * (CELL + GAP)))
    # 右下角印章
    d = ImageDraw.Draw(canvas)
    s = 22
    d.rectangle([W - PAD - s, H - PAD - s, W - PAD, H - PAD], fill=(160, 61, 44))
    return canvas, sources


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = []
    for slug, chars, name in PIECES:
        img, sources = compose(chars, name)
        img.save(OUT / f"{slug}.png", optimize=True)
        n_real = sources.count("real")
        meta.append({"slug": slug, "text": chars, "name": name,
                     "real": n_real, "ai": len(sources) - n_real})
        print(f"{chars} × {name}: 真跡 {n_real}、AI {len(sources)-n_real} → {slug}.png")
    (OUT / "showcase.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("完成")


if __name__ == "__main__":
    main()
