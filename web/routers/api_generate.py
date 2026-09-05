"""求字 API：代理到獨立的生成服務（fontdiff 環境，port 8135）。

/api/generate/char    — 單字：真跡優先（集字），無真跡則 AI 生成（K 候選＋重排）
/api/generate/status  — 生成服務是否在線
"""
import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent
FONTS_DIR = PROJECT_ROOT / "Fonts" / "my_fonts"
INDEX_PATH = PROJECT_ROOT / "data" / "index" / "character_index.json"
GEN_SERVER = "http://127.0.0.1:8135"

MERGE = {"zhiyong_00": "智永", "shen_yinmo_01": "沈尹默", "shen_yinmo_08": "沈尹默",
         "shen_yinmo_09": "沈尹默", "shen_yinmo_10": "沈尹默", "liu_gongquan_02": "柳公權",
         "ouyang_xun_03": "歐陽詢", "zhao_mengfu_04": "趙孟頫", "yu_shinan_06": "虞世南",
         "yan_zhenqing_07": "顏真卿"}
NAME2LABEL = {"智永": "zhiyong", "歐陽詢": "ouyang_xun", "虞世南": "yu_shinan",
              "顏真卿": "yan_zhenqing", "柳公權": "liu_gongquan",
              "趙孟頫": "zhao_mengfu", "沈尹默": "shen_yinmo"}
# 依 held-out 同字真跡評估（凍結評估器）的各書法家 style match 給的誠實可靠度
RELIABILITY = {"虞世南": "高", "沈尹默": "高", "智永": "中",
               "顏真卿": "低", "趙孟頫": "低", "柳公權": "低", "歐陽詢": "低"}


@lru_cache(maxsize=1)
def _index():
    """char → 顯示名 → [(font_id, filename), ...]"""
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    table = {}
    for char, cals in data["character_map"].items():
        by_name = {}
        for cal, instances in cals.items():
            name = MERGE.get(cal)
            if not name:
                continue
            for inst in instances:
                fid, fn = inst.get("font_id"), inst.get("filename")
                if fid and fn and (FONTS_DIR / fid / fn).exists():
                    by_name.setdefault(name, []).append((fid, fn))
        if by_name:
            table[char] = by_name
    return table


def _real_glyphs(char: str, name: str) -> list[str]:
    return [f"/fonts/{fid}/{fn}" for fid, fn in _index().get(char, {}).get(name, [])]


@router.get("/char")
async def generate_char(char: str = Query(..., min_length=1, max_length=1),
                        name: str = Query(...),
                        k: int = Query(5, ge=1, le=8),
                        seed: int = Query(0),
                        prefer_real: bool = Query(True)):
    if name not in NAME2LABEL:
        raise HTTPException(400, "未知的書法家")
    real = _real_glyphs(char, name)
    base = {"char": char, "name": name, "reliability": RELIABILITY[name],
            "real_glyphs": real}

    # 集字模式：有真跡就直接用，不進生成（秒回）
    if prefer_real and real:
        return {**base, "source": "real", "best": None, "candidates": []}

    q = urllib.parse.urlencode({"char": char, "cal": NAME2LABEL[name], "k": k, "seed": seed})

    def _call():
        with urllib.request.urlopen(f"{GEN_SERVER}/generate?{q}", timeout=180) as r:
            return json.loads(r.read().decode())

    try:
        data = await asyncio.to_thread(_call)   # 生成約 2 秒/候選，不能卡事件迴圈
    except urllib.error.HTTPError as e:
        raise HTTPException(e.code, e.read().decode(errors="ignore")[:200])
    except urllib.error.URLError:
        raise HTTPException(503, "生成服務目前離線（此功能需要 GPU，僅在研究工作站上提供）")
    return {**base, "source": "ai", "content_source": data["content_source"],
            "best": data["best"], "candidates": data["candidates"],
            "content_png": data["content_png"]}


@router.get("/status")
async def generate_status():
    try:
        with urllib.request.urlopen(f"{GEN_SERVER}/health", timeout=3) as r:
            return {"online": True, **json.loads(r.read().decode())}
    except Exception:
        return {"online": False}
