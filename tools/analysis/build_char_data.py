"""
字元補充資料生成工具

生成 data/index/char_data.json，包含：
  - freq_rank : 字頻排名（1 = 最常用，數字越大越罕用）
  - strokes   : 繁體字筆畫數
  - radical   : 部首（康熙字典 214 部首）

使用方式：
    python tools/analysis/build_char_data.py

資料來源：
  - 字頻：内嵌現代漢語常用字頻率表（3500 字）
  - 筆畫：優先使用 Unihan 資料（kTotalStrokes），備用內建表
  - 部首：Unihan 資料（kRSUnicode）→ 康熙 214 部首
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


# ── 康熙 214 部首表 ────────────────────────────────────────────────────────────
# 部首編號 → 部首字元
# 來源：Unicode CJK Radicals，編號 1-214 對應《康熙字典》
_KANGXI_RADICALS = {
    1:"一",2:"丨",3:"丶",4:"丿",5:"乙",6:"亅",7:"二",8:"亠",9:"人",10:"儿",
    11:"入",12:"八",13:"冂",14:"冖",15:"冫",16:"几",17:"凵",18:"刀",19:"力",20:"勹",
    21:"匕",22:"匚",23:"匸",24:"十",25:"卜",26:"卩",27:"厂",28:"厶",29:"又",30:"口",
    31:"囗",32:"土",33:"士",34:"夂",35:"夊",36:"夕",37:"大",38:"女",39:"子",40:"宀",
    41:"寸",42:"小",43:"尢",44:"尸",45:"屮",46:"山",47:"巛",48:"工",49:"己",50:"巾",
    51:"干",52:"幺",53:"广",54:"廴",55:"廾",56:"弋",57:"弓",58:"彐",59:"彡",60:"彳",
    61:"心",62:"戈",63:"戶",64:"手",65:"支",66:"攴",67:"文",68:"斗",69:"斤",70:"方",
    71:"无",72:"日",73:"曰",74:"月",75:"木",76:"欠",77:"止",78:"歹",79:"殳",80:"毋",
    81:"比",82:"毛",83:"氏",84:"气",85:"水",86:"火",87:"爪",88:"父",89:"爻",90:"爿",
    91:"片",92:"牙",93:"牛",94:"犬",95:"玄",96:"玉",97:"瓜",98:"瓦",99:"甘",100:"生",
    101:"用",102:"田",103:"疋",104:"疒",105:"癶",106:"白",107:"皮",108:"皿",109:"目",110:"矛",
    111:"矢",112:"石",113:"示",114:"禸",115:"禾",116:"穴",117:"立",118:"竹",119:"米",120:"糸",
    121:"缶",122:"网",123:"羊",124:"羽",125:"老",126:"而",127:"耒",128:"耳",129:"聿",130:"肉",
    131:"臣",132:"自",133:"至",134:"臼",135:"舌",136:"舛",137:"舟",138:"艮",139:"色",140:"艸",
    141:"虍",142:"虫",143:"血",144:"行",145:"衣",146:"襾",147:"見",148:"角",149:"言",150:"谷",
    151:"豆",152:"豕",153:"豸",154:"貝",155:"赤",156:"走",157:"足",158:"身",159:"車",160:"辛",
    161:"辰",162:"辵",163:"邑",164:"酉",165:"釆",166:"里",167:"金",168:"長",169:"門",170:"阜",
    171:"隶",172:"隹",173:"雨",174:"青",175:"非",176:"面",177:"革",178:"韋",179:"韭",180:"音",
    181:"頁",182:"風",183:"飛",184:"食",185:"首",186:"香",187:"馬",188:"骨",189:"高",190:"髟",
    191:"鬥",192:"鬯",193:"鬲",194:"鬼",195:"魚",196:"鳥",197:"鹵",198:"鹿",199:"麥",200:"麻",
    201:"黃",202:"黍",203:"黑",204:"黹",205:"黽",206:"鼎",207:"鼓",208:"鼠",209:"鼻",210:"齊",
    211:"齒",212:"龍",213:"龜",214:"龠",
}


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


def get_unihan_data(chars):
    """從 Unicode Unihan 資料庫下載筆畫數與部首資料

    提取：
    - kTotalStrokes（筆畫數）→ Unihan_IRGSources.txt
    - kRSUnicode（部首-剩餘筆畫）→ Unihan_RadicalStrokeCounts.txt

    回傳：(stroke_map, radical_map)
    """
    char_set = set(chars)
    url = "https://unicode.org/Public/UCD/latest/ucd/Unihan.zip"
    print(f"[Unihan] 從 {url} 下載（約 6 MB）…")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            raw = resp.read()

        stroke_map = {}
        radical_map = {}

        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            # kTotalStrokes 和 kRSUnicode 都在 Unihan_IRGSources.txt
            with z.open("Unihan_IRGSources.txt") as f:
                content = f.read().decode('utf-8')

            for line in content.splitlines():
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) < 3:
                    continue

                field = parts[1]
                if field not in ('kTotalStrokes', 'kRSUnicode'):
                    continue

                try:
                    cp  = int(parts[0].lstrip('U+'), 16)
                    ch  = chr(cp)
                    if ch not in char_set:
                        continue

                    if field == 'kTotalStrokes':
                        val = parts[2].strip().split()[0]
                        stroke_map[ch] = int(val)
                    elif field == 'kRSUnicode':
                        # 格式："85.7" 或 "85'.7"（' 表示簡化部首變體）
                        # 取第一個值（可能有多組，如 "85.7 109.2"）
                        rs_val = parts[2].strip().split()[0]
                        radical_num = int(rs_val.split('.')[0].rstrip("'"))
                        if 1 <= radical_num <= 214:
                            radical_char = _KANGXI_RADICALS.get(radical_num, "")
                            if radical_char:
                                radical_map[ch] = radical_char
                except (ValueError, IndexError):
                    pass

        print(f"[Unihan] 筆畫：{len(stroke_map)}/{len(chars)} 個字元")
        print(f"[Unihan] 部首：{len(radical_map)}/{len(chars)} 個字元")
        return stroke_map, radical_map
    except Exception as e:
        print(f"[Unihan] 下載失敗：{e}")
        return {}, {}


def build_char_data():
    """主流程：建立 char_data.json"""
    chars = get_char_list()

    # 1. 從 Unihan 取得筆畫數 + 部首
    stroke_map, radical_map = get_unihan_data(chars)

    # 補充內建備用筆畫表
    missing_before = sum(1 for c in chars if c not in stroke_map)
    for c in chars:
        if c not in stroke_map and c in _STROKE_FALLBACK:
            stroke_map[c] = _STROKE_FALLBACK[c]
    missing_after = sum(1 for c in chars if c not in stroke_map)
    print(f"[備用表] 補充 {missing_before - missing_after} 個字元筆畫")
    if missing_after > 0:
        print(f"[警告] 仍有 {missing_after} 個字元缺少筆畫數（以 0 填充）")

    radical_missing = sum(1 for c in chars if c not in radical_map)
    if radical_missing > 0:
        print(f"[警告] 有 {radical_missing} 個字元缺少部首資料")

    # 2. 組合結果
    char_data = {}
    for c in chars:
        entry = {
            "freq_rank": _freq_dict.get(c, 9999),
            "strokes":   stroke_map.get(c, 0),
        }
        if c in radical_map:
            entry["radical"] = radical_map[c]
        char_data[c] = entry

    # 3. 儲存
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(char_data, f, ensure_ascii=False, indent=2)

    freq_ok    = sum(1 for v in char_data.values() if v['freq_rank'] < 9999)
    stroke_ok  = sum(1 for v in char_data.values() if v['strokes'] > 0)
    radical_ok = sum(1 for v in char_data.values() if 'radical' in v)
    print(f"\n[完成] 已儲存至 {OUT_FILE}")
    print(f"  字頻已知: {freq_ok}/{len(chars)}")
    print(f"  筆畫已知: {stroke_ok}/{len(chars)}")
    print(f"  部首已知: {radical_ok}/{len(chars)}")


if __name__ == "__main__":
    build_char_data()
