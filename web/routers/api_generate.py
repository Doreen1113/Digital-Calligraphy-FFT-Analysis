"""集字 API：代理到獨立的生成服務（fontdiff 環境，port 8135）。

/api/generate/char    — 單字：真跡優先（集字），無真跡則 AI 生成（K 候選＋重排）
/api/generate/status  — 生成服務是否在線
"""
import asyncio
import json
import os
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
# 本機開發：同一台工作站上的 gen_server（fontdiff 環境，port 8135）。
# 公開部署（Render）：改用 Modal 上的 GPU serverless function，
# 兩者路徑不同（Modal 每個 function 各自一個網域），故用兩個獨立的環境變數覆寫。
GEN_SERVER = os.environ.get("GEN_SERVER_URL", "http://127.0.0.1:8135")
GEN_GENERATE_URL = os.environ.get("GEN_GENERATE_URL", f"{GEN_SERVER}/generate")
GEN_HEALTH_URL = os.environ.get("GEN_HEALTH_URL", f"{GEN_SERVER}/health")
PREBUILT_DIR = PROJECT_ROOT / "web" / "static" / "generated"

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
def _prebuilt() -> dict:
    """預先生成的 AI 補字快取索引：{書法家: {unicode_hex: {...}}}。

    使無 GPU 的部署環境（如 Render）也能提供常用字的集字結果；
    快取由 tools/prebuild_generated.py 於具 GPU 的機器上離線產生。
    """
    p = PREBUILT_DIR / "index.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


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
                        k: int = Query(1, ge=1, le=8),
                        seed: int = Query(0),
                        prefer_real: bool = Query(True)):
    if name not in NAME2LABEL:
        raise HTTPException(400, "未知的書法家")
    real = _real_glyphs(char, name)
    base = {"char": char, "name": name, "reliability": RELIABILITY[name],
            "real_glyphs": real}

    # 1) 集字模式：有真跡就直接用，不進生成（秒回）
    if prefer_real and real:
        return {**base, "source": "real", "best": None, "candidates": []}

    # 2) 預先生成的快取：無 GPU 環境亦可服務常用字
    hexname = f"{ord(char):05X}"
    entry = _prebuilt().get(name, {}).get(hexname)
    if entry and (PREBUILT_DIR / NAME2LABEL[name] / f"{hexname}.png").exists():
        return {**base, "source": "cache",
                "content_source": entry.get("content_source", "kaiu"),
                "best": {"url": f"/static/generated/{NAME2LABEL[name]}/{hexname}.png",
                         "score": entry.get("score", 0.0), "pred": entry.get("pred", "")},
                "candidates": []}

    # 3) 即時生成（需 GPU 後端）

    q = urllib.parse.urlencode({"char": char, "cal": NAME2LABEL[name], "k": k, "seed": seed})

    def _call():
        with urllib.request.urlopen(f"{GEN_GENERATE_URL}?{q}", timeout=180) as r:
            return json.loads(r.read().decode())

    try:
        data = await asyncio.to_thread(_call)   # 生成約 2 秒/候選，不能卡事件迴圈
    except urllib.error.HTTPError as e:
        # 上游（gen_server）回傳的是 {"detail": "..."} 這種 FastAPI 錯誤格式，
        # 直接把整段原始 JSON 塞進 detail 會讓使用者看到雙重編碼的原始字串；
        # 這裡解析出真正的錯誤文字再轉發。
        try:
            body = json.loads(e.read().decode(errors="ignore"))
            msg = body.get("detail", str(body))
        except Exception:
            msg = f"生成失敗（{e.code}）"
        raise HTTPException(e.code, msg)
    except urllib.error.URLError:
        raise HTTPException(503, "生成服務目前離線（此功能需要 GPU，僅在研究工作站上提供）")
    return {**base, "source": "ai", "content_source": data["content_source"],
            "best": data["best"], "candidates": data["candidates"],
            "content_png": data["content_png"]}


@router.get("/status")
async def generate_status():
    prebuilt = _prebuilt()
    info = {"prebuilt_chars": sum(len(v) for v in prebuilt.values()),
            "prebuilt_calligraphers": len(prebuilt)}
    try:
        with urllib.request.urlopen(GEN_HEALTH_URL, timeout=3) as r:
            return {"online": True, **info, **json.loads(r.read().decode())}
    except Exception:
        return {"online": False, **info}
