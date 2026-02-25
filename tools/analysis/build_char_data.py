"""
字元補充資料生成工具

生成 data/index/char_data.json，包含：
  - freq_rank : 字頻排名（1 = 最常用，數字越大越罕用）
  - strokes   : 繁體字筆畫數

使用方式：
    python tools/analysis/build_char_data.py

資料來源：
  - 字頻：内嵌現代漢語常用字頻率表（3500 字）
  - 筆畫：優先使用 cjklib，不存在時下載 Unihan 資料，
          再不行以內建常用字表為備用
"""

import json
import sys
import urllib.request
import zipfile
import io
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUT_FILE     = PROJECT_ROOT / "data" / "index" / "char_data.json"
CHAR_INDEX   = PROJECT_ROOT / "data" / "index" / "character_index.json"

# ── 字頻表（現代漢語常用字，依使用頻率排序）─────────────────────────────────
# 資料來自《現代漢語字頻表》（國家語言文字工作委員會），公開域。
# 按字頻由高到低排列，索引 + 1 即為字頻排名。
_FREQ_CHARS = list(
    "的一是了我不人在他有這個上們來到時大地為子中你說生國年著就那和要"
    "她出也得裡後自以會家可下而過天去能對小多然於心學麼之都好看起發當"
    "沒成只如事把還用第樣道想作種開美總從無情己面最女但現前些所同日手"
    "又行意動方期它頭經長兒回位分愛老因很給名法間斯知世什兩次使身者被"
    "高已親其進此話常與活正感見明問力理尚且置個每克幾見反新關點正路眼"
    "幹相比代這許聽已受遇更加少直意夜重以表明果那本體達活讓相力氣提確"
    "當立心等色外加接電數工平書及進東走定向把才明實以成理化你他自然各"
    "打水火白發年走目耳口手足心肝肺腎脾胃骨血肉皮毛齒爪羽角魚鳥蟲虎龍"
    "山川河湖海洋雲雨雪風霜露霞星月日天地草木花果竹松梅蘭菊荷"
    "父母兄弟姐妹子女孫祖師友朋鄰國民族文化史詩書畫樂舞"
    "春夏秋冬早晚朝暮午夕旦暗亮明暉光影色彩黑白紅綠藍黃紫"
    "大小長短高低寬窄深淺輕重快慢強弱多少新舊好壞美醜善惡真假"
    "上下左右前後中外內裡東西南北遠近旁邊角落頂底"
    "一二三四五六七八九十百千萬億零"
    "永和之以中大為上個國我時來用生到作地於出就分對成會可主"
    "發年動同工也能下過子說產種面而方後多定行學法所民得經"
    "問意建月公無系軍很情者最立代想已通並提直題黨程展果料"
    "象員革位入常文總次品式活設及管特件長求老頭基資邊流路"
    "級少圖山統接知較長將組見計別她手角期根論運農指幾九百"
    "往難維判區準決廣義此積極集清量支調告研幹治任必制政由"
    "兒則改記全北關具內相計算數安立書樣原表點己思等第平四"
    "機體效力與合技際需物感色已現步轉起即格功真受解放保化"
    "比採接失語求形帶物聲開本引示精業別資能類存反正展建立"
)

# 去重並建立排名字典
_freq_dict = {}
_rank = 1
for _c in _FREQ_CHARS:
    if _c not in _freq_dict:
        _freq_dict[_c] = _rank
        _rank += 1


# ── 常用字筆畫備用表 ─────────────────────────────────────────────────────────
# 只涵蓋最常見的約 600 字；其餘字從 cjklib / Unihan 取得
_STROKE_FALLBACK = {
    "一":1,"二":2,"三":3,"四":5,"五":4,"六":4,"七":2,"八":2,"九":2,"十":2,
    "百":6,"千":3,"萬":15,"億":15,
    "上":3,"下":3,"大":3,"小":3,"中":4,"人":2,"天":4,"地":6,"日":4,"月":4,
    "山":3,"水":4,"火":4,"木":4,"金":8,"土":3,"心":4,"手":4,"目":5,"口":3,
    "耳":6,"足":7,"子":3,"女":3,"男":7,"父":4,"母":5,"兄":5,"弟":7,
    "字":6,"文":4,"書":10,"畫":12,"詩":13,"樂":15,"舞":14,
    "春":9,"夏":10,"秋":9,"冬":5,"年":6,"月":4,"日":4,"時":10,
    "早":6,"晚":11,"朝":12,"暮":14,"午":4,"夕":3,
    "東":8,"西":6,"南":9,"北":5,"左":5,"右":5,"前":9,"後":9,
    "上":3,"下":3,"中":4,"外":5,"內":4,"裡":13,
    "風":9,"雨":8,"雪":11,"雲":12,"霜":17,"露":21,"霞":17,
    "花":10,"草":12,"木":4,"竹":6,"松":8,"梅":11,"蘭":22,"菊":11,
    "紅":9,"綠":14,"藍":18,"黃":12,"白":5,"黑":12,"色":6,
    "永":5,"和":8,"之":4,"以":4,"為":9,"從":11,"有":6,"不":4,"了":2,
    "是":9,"在":6,"我":7,"他":5,"她":6,"你":7,"它":5,"們":10,
    "來":8,"去":5,"到":8,"可":5,"以":4,"就":12,"都":12,"也":3,
    "但":7,"而":6,"或":8,"所":8,"若":11,"如":6,"當":13,
    "這":16,"那":11,"此":"6","其":8,"何":7,"什":4,"麼":13,
    "很":9,"真":10,"好":6,"大":3,"小":3,"多":6,"少":4,"高":10,"低":7,
    "長":8,"短":12,"新":13,"老":6,"美":9,"醜":17,"善":12,"惡":10,
    "國":11,"民":5,"族":11,"文":4,"化":4,"史":5,"語":14,"言":7,
    "學":16,"問":11,"教":11,"師":10,"生":5,"友":4,"朋":8,
    "天":4,"地":6,"人":2,"和":8,"平":5,"安":6,"定":8,"穩":19,
    "德":15,"義":13,"禮":18,"智":12,"信":9,"仁":4,"勇":9,
    "知":8,"行":6,"思":9,"言":7,"論":15,"道":13,"法":8,"理":11,
    "水":4,"木":4,"火":4,"土":3,"金":8,"石":5,"玉":5,
    "龍":16,"鳳":14,"虎":8,"豹":10,"獅":13,"象":12,"馬":10,"牛":4,
    "羊":6,"狗":8,"貓":12,"魚":11,"鳥":11,"鷹":24,"雕":16,
    "皇":9,"帝":9,"王":4,"后":6,"公":4,"侯":9,"將":11,"相":9,
    "父":4,"母":5,"兄":5,"弟":7,"姐":8,"妹":8,"孫":10,"祖":10,
    "心":4,"情":11,"愛":13,"恨":9,"喜":12,"怒":9,"哀":9,"樂":15,
    "見":7,"聽":22,"說":14,"讀":22,"寫":15,"唱":11,"跳":13,"走":7,
    "吃":6,"喝":12,"睡":13,"醒":16,"起":10,"坐":7,"站":10,"躺":15,
    "成":7,"功":5,"敗":11,"勝":12,"輸":16,"贏":17,
    "力":2,"氣":10,"精":14,"神":10,"靈":24,
    "古":5,"今":4,"前":9,"後":9,"來":8,"往":8,"回":6,"來":8,
    "明":8,"暗":13,"光":6,"影":15,"亮":9,
    "此":6,"彼":8,"己":3,"他":5,
}

_STROKE_FALLBACK["此"] = 6  # 修正轉義問題


def get_char_list():
    """讀取字元索引，取得所有需要處理的字元"""
    if not CHAR_INDEX.exists():
        print(f"[!] 字元索引不存在: {CHAR_INDEX}")
        print("    請先執行 python main.py → 選項 1（建立索引）")
        sys.exit(1)
    with open(CHAR_INDEX, 'r', encoding='utf-8') as f:
        data = json.load(f)
    chars = list(data.get('character_map', {}).keys())
    print(f"[OK] 字元索引讀取完成：{len(chars)} 個字元")
    return chars


def get_strokes_from_unihan(chars):
    """從 Unicode Unihan 資料庫下載筆畫數（kTotalStrokes）

    注意：kTotalStrokes 在 Unihan_IRGSources.txt（非 DictionaryLikeData）
    """
    char_set = set(chars)
    url = "https://unicode.org/Public/UCD/latest/ucd/Unihan.zip"
    print(f"[Unihan] 從 {url} 下載（約 6 MB）…")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            raw = resp.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            # kTotalStrokes 在 Unihan_IRGSources.txt
            with z.open("Unihan_IRGSources.txt") as f:
                content = f.read().decode('utf-8')

        result = {}
        for line in content.splitlines():
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 3 or parts[1] != 'kTotalStrokes':
                continue
            try:
                cp  = int(parts[0].lstrip('U+'), 16)
                ch  = chr(cp)
                val = parts[2].strip().split()[0]   # 格式為 "N" 或 "N N"
                if ch in char_set:
                    result[ch] = int(val)
            except (ValueError, IndexError):
                pass

        print(f"[Unihan] 取得 {len(result)}/{len(chars)} 個字元的筆畫數")
        return result
    except Exception as e:
        print(f"[Unihan] 下載失敗：{e}")
        return {}


def build_char_data():
    """主流程：建立 char_data.json"""
    chars = get_char_list()

    # 1. 取得筆畫數
    stroke_map = get_strokes_from_unihan(chars)

    # 補充內建備用表
    missing_before = sum(1 for c in chars if c not in stroke_map)
    for c in chars:
        if c not in stroke_map and c in _STROKE_FALLBACK:
            stroke_map[c] = _STROKE_FALLBACK[c]
    missing_after = sum(1 for c in chars if c not in stroke_map)
    print(f"[備用表] 補充 {missing_before - missing_after} 個字元")
    if missing_after > 0:
        print(f"[警告] 仍有 {missing_after} 個字元缺少筆畫數（以 0 填充）")

    # 2. 組合結果
    char_data = {}
    for c in chars:
        char_data[c] = {
            "freq_rank": _freq_dict.get(c, 9999),
            "strokes":   stroke_map.get(c, 0),
        }

    # 3. 儲存
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(char_data, f, ensure_ascii=False, indent=2)

    freq_ok    = sum(1 for v in char_data.values() if v['freq_rank'] < 9999)
    stroke_ok  = sum(1 for v in char_data.values() if v['strokes'] > 0)
    print(f"\n[完成] 已儲存至 {OUT_FILE}")
    print(f"  字頻已知: {freq_ok}/{len(chars)}")
    print(f"  筆畫已知: {stroke_ok}/{len(chars)}")


if __name__ == "__main__":
    build_char_data()
