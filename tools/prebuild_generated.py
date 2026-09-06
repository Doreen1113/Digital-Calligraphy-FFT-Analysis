"""預先生成常用字的 AI 補字快取（在 fontdiff 環境、GPU 機器上執行一次）。

產出 web/static/generated/{書法家}/{unicode_hex}.png ＋ index.json，
使線上版（無 GPU）也能提供「求字」結果：真跡優先、其次讀取此快取、
兩者皆無時才回報需要即時生成。

用法：
  conda activate fontdiff
  python tools/prebuild_generated.py [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CALLI = Path(__file__).parent.parent
OUT = CALLI / "web" / "static" / "generated"
GEN_SERVER = "http://127.0.0.1:8135"

NAME2LABEL = {"智永": "zhiyong", "歐陽詢": "ouyang_xun", "虞世南": "yu_shinan",
              "顏真卿": "yan_zhenqing", "柳公權": "liu_gongquan",
              "趙孟頫": "zhao_mengfu", "沈尹默": "shen_yinmo"}
MERGE = {"zhiyong_00": "智永", "shen_yinmo_01": "沈尹默", "shen_yinmo_08": "沈尹默",
         "shen_yinmo_09": "沈尹默", "shen_yinmo_10": "沈尹默", "liu_gongquan_02": "柳公權",
         "ouyang_xun_03": "歐陽詢", "zhao_mengfu_04": "趙孟頫", "yu_shinan_06": "虞世南",
         "yan_zhenqing_07": "顏真卿"}


def real_chars() -> dict[str, set]:
    idx = json.loads((CALLI / "data" / "index" / "character_index.json").read_text(encoding="utf-8"))
    have = {n: set() for n in NAME2LABEL}
    for ch, cals in idx["character_map"].items():
        for cal in cals:
            if cal in MERGE:
                have[MERGE[cal]].add(ch)
    return have


def generate(char: str, name: str, k: int = 5) -> dict | None:
    q = urllib.parse.urlencode({"char": char, "cal": NAME2LABEL[name], "k": k, "seed": 0})
    try:
        with urllib.request.urlopen(f"{GEN_SERVER}/generate?{q}", timeout=180) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  [fail] {name} {char}: {e}", flush=True)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="每位書法家最多生成幾個字（0=全部）")
    ap.add_argument("--chars", default="common_chars.json",
                    help="字表檔名（experiments/ 下），如 common_chars_full.json")
    ap.add_argument("--k", type=int, default=5, help="每字生成幾個候選供重排")
    args = ap.parse_args()

    common = json.loads((CALLI / "experiments" / args.chars).read_text(encoding="utf-8"))
    have = real_chars()
    index: dict[str, dict[str, dict]] = {}
    idx_path = OUT / "index.json"
    if idx_path.exists():
        index = json.loads(idx_path.read_text(encoding="utf-8"))

    todo = []
    for name in NAME2LABEL:
        miss = [c for c in common if c not in have[name]]
        if args.limit:
            miss = miss[:args.limit]
        todo += [(name, c) for c in miss
                 if f"{ord(c):05X}" not in index.get(name, {})]
    print(f"待生成 {len(todo)} 張", flush=True)

    t0 = time.time()
    for i, (name, char) in enumerate(todo, 1):
        j = generate(char, name, args.k)
        if not j:
            continue
        d = OUT / NAME2LABEL[name]
        d.mkdir(parents=True, exist_ok=True)
        hexname = f"{ord(char):05X}"
        (d / f"{hexname}.png").write_bytes(base64.b64decode(j["best"]["png"]))
        index.setdefault(name, {})[hexname] = {
            "char": char,
            "score": round(j["best"]["score"], 4),
            "pred": j["best"]["pred"],
            "content_source": j["content_source"],
        }
        if i % 25 == 0 or i == len(todo):
            el = time.time() - t0
            idx_path.parent.mkdir(parents=True, exist_ok=True)
            idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {i}/{len(todo)}　已用 {el/60:.1f} 分　預估剩餘 {(len(todo)-i)*el/i/60:.1f} 分", flush=True)

    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in index.values())
    size = sum(p.stat().st_size for p in OUT.rglob("*.png")) / 1024 / 1024
    print(f"\n完成：快取 {total} 張、{size:.1f} MB → {OUT}", flush=True)


if __name__ == "__main__":
    main()
