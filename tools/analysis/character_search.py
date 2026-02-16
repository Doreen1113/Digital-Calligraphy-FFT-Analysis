"""
字元搜尋與過濾工具
根據不同條件搜尋字元：書法家數量、部首、筆畫、使用頻率等
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import Counter

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils import get_config


# 常用字列表（前 1000 個常用字）
COMMON_CHARACTERS = """
的一是在不了有和人這中大為上個國我以要他時來用們生到作地於出就分對成會
可主發年動同工也能下過子說產種面而方後多定行學法所民得經十三之進著等部
度家電力裡如水化高自二理起小物現實加量都兩體制機當使點從業本去把性好應
開它合還因由其些然前外天政四日那社義事平形相全表間樣與關各重新線內數正
心反你明看原又麼利比或但質氣第向道命此變條只沒結解問意建月公無系軍很情
者最立代想已通並提直題黨程展五果料象員革位入常文總次品式活設及管特件長
求老頭基資邊流路級少圖山統接知較將組見計別她手角期根論運農指幾九區強放
決西被幹做必戰先回則任取據處隊南給色光門即保治北造百規熱領七海口東導器
壓志世金增爭濟階油思術極交受聯什認六共權收證改清己美再採轉更單風切打白
教速花帶安場身車例真務具萬每目至達走積示議聲報鬥完類八離華名確才科張信
馬節話米整空元況今集溫傳土許步群廣石記需段研界拉林律叫且究觀越織裝影算
低持音眾書布复容兒須際商非驗連斷深難近礦千週委素技備半辦青省列習響約支
般史感勞便團往酸歷市克何除消構府稱太準精值號率族維劃選標寫存候毛親快效
斯院查江型眼王按格養易置派層片始卻專狀育廠京識適屬圓包火住調滿縣局照參
紅細引聽該鐵價嚴首底液官德隨病蘇失爾死講配女黃推顯談罪神藝呢席含企望密
批營項防舉球英氧勢告李台落木幫輪破亞師圍注遠字材排供河態封另施減樹溶怎
止案言士均武固葉魚波視僅費緊愛左章早朝害續輕服試食充兵源判護司足某練差
致板田降黑犯負擊范繼興似餘堅曲輸修故城夫夠送筆船佔右財吃富春職覺漢畫功
巴跟雖雜飛檢吸助昇陽互初創抗考投壞策古徑換未跑留鋼曾端責站簡述錢副盡帝
射草衝承獨令限阿宣環雙請超微讓控州良軸找否紀益依優頂礎載倒房突坐粉敵略
客袁冷勝絕析塊劑測絲協訴念陳仍羅鹽友洋錯苦夜刑移頻逐靠混母短皮終聚汽村
雲哪既距衛停烈央察燒迅境若印洲刻括激孔搞甚室待核校散侵吧甲遊久菜味舊模
湖貨損預阻毫普穩乙媽植息擴銀語揮酒守拿序紙醫缺雨嗎針劉啊急唱誤訓願審附
獲茶鮮糧斤孩脫硫肥善龍演父漸血歡械掌歌沙剛攻謂盾討晚粒亂燃矛乎殺藥寧魯
貴鐘煤讀班伯香介迫句豐培握蘭擔弦蛋沉假穿執答樂誰順煙縮徵臉喜松腳困異免
背星福買染井概慢怕磁倍祖皇促靜補評翻肉踐尼衣寬揚棉希傷操垂秋宜氫套督振
架亮末憲慶編牛觸映雷銷詩座居抓裂胞呼娘景威綠晶厚盟衡雞孫延危膠屋鄉臨陸
顧掉呀燈歲措束遭架搖飯遇挺窮奮劍亡循"""


def load_character_index() -> Optional[Dict]:
    """載入同字索引"""
    config = get_config()
    index_path = config.get_index_path('character_index')

    if not os.path.exists(index_path):
        print("[Error] 同字索引不存在")
        print("請先執行「建立/更新資料索引」")
        return None

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_by_calligrapher_count(char_map: Dict, min_count: int = 2, max_count: int = 4) -> List[str]:
    """
    依書法家數量過濾

    Args:
        char_map: 字元索引對應表
        min_count: 最少書法家數量
        max_count: 最多書法家數量

    Returns:
        符合條件的字元列表
    """
    result = []
    for char, calligraphers in char_map.items():
        count = len(calligraphers)
        if min_count <= count <= max_count:
            result.append(char)
    return sorted(result)


def filter_by_common_characters(char_map: Dict, top_n: int = 500) -> List[str]:
    """
    依常用字過濾

    Args:
        char_map: 字元索引對應表
        top_n: 前 N 個常用字

    Returns:
        在字庫中的常用字列表
    """
    # 取前 top_n 個常用字
    common_set = set(COMMON_CHARACTERS.replace('\n', '')[:top_n])

    # 找出在字庫中的常用字
    result = [char for char in common_set if char in char_map]
    return sorted(result)


def filter_by_radical(char_map: Dict, radical: str) -> List[str]:
    """
    依部首過濾（簡易版，使用 Unicode 區塊判斷）

    Args:
        char_map: 字元索引對應表
        radical: 部首字元

    Returns:
        包含該部首的字元列表
    """
    result = []

    # 簡易判斷：檢查字元是否包含部首字元
    # 注意：這是一個簡化版本，真正的部首分析需要專門的字典
    for char in char_map.keys():
        if radical in char:
            result.append(char)

    return sorted(result)


def search_characters(char_map: Dict, query: str) -> List[str]:
    """
    模糊搜尋字元

    Args:
        char_map: 字元索引對應表
        query: 搜尋關鍵字

    Returns:
        包含關鍵字的字元列表
    """
    result = []
    for char in char_map.keys():
        if query in char or char in query:
            result.append(char)
    return sorted(result)


def get_character_stats(char_map: Dict) -> Dict:
    """
    取得字元統計資訊

    Args:
        char_map: 字元索引對應表

    Returns:
        統計資訊字典
    """
    total_chars = len(char_map)
    calligrapher_counts = Counter(len(cals) for cals in char_map.values())

    # 計算常用字比例
    common_set = set(COMMON_CHARACTERS.replace('\n', ''))
    common_in_db = sum(1 for char in char_map if char in common_set)

    return {
        'total_characters': total_chars,
        'by_calligrapher_count': dict(calligrapher_counts),
        'common_characters': common_in_db,
        'common_percentage': (common_in_db / total_chars * 100) if total_chars > 0 else 0
    }


def print_search_results(characters: List[str], title: str, max_display: int = 50):
    """
    列印搜尋結果

    Args:
        characters: 字元列表
        title: 標題
        max_display: 最多顯示數量
    """
    print(f"\n{title}")
    print("-" * 70)
    print(f"找到 {len(characters)} 個字元")

    if not characters:
        print("（無結果）")
        return

    # 分行顯示
    display_chars = characters[:max_display]
    for i in range(0, len(display_chars), 20):
        line = ''.join(display_chars[i:i+20])
        print(f"  {line}")

    if len(characters) > max_display:
        print(f"  ... 還有 {len(characters) - max_display} 個字")

    print()


def interactive_search():
    """互動式搜尋"""
    print("\n" + "="*70)
    print(" 字元搜尋與過濾工具")
    print("="*70)

    # 載入索引
    char_index = load_character_index()
    if not char_index:
        return

    char_map = char_index.get('character_map', {})

    # 顯示統計
    stats = get_character_stats(char_map)
    print(f"\n 字庫統計:")
    print(f"   總字數: {stats['total_characters']}")
    print(f"   常用字: {stats['common_characters']} ({stats['common_percentage']:.1f}%)")
    print(f"\n 依書法家數量分布:")
    for count in sorted(stats['by_calligrapher_count'].keys(), reverse=True):
        num = stats['by_calligrapher_count'][count]
        print(f"   {count} 位書法家: {num} 個字")

    while True:
        print("\n" + "-"*70)
        print(" 搜尋選項:")
        print("-"*70)
        print("  1. 依書法家數量過濾")
        print("  2. 搜尋常用字")
        print("  3. 模糊搜尋")
        print("  4. 顯示統計資訊")
        print("  0. 返回")
        print("-"*70)

        choice = input("\n請選擇 (0-4): ").strip()

        if choice == '0':
            break

        elif choice == '1':
            print("\n依書法家數量過濾")
            print("  1: 只有 1 位書法家")
            print("  2: 2 位書法家")
            print("  3: 3 位書法家")
            print("  4: 4 位書法家（共有字）")
            print("  2+: 2 位以上")
            print("  3+: 3 位以上")

            sub_choice = input("\n請選擇: ").strip()

            if sub_choice == '1':
                result = filter_by_calligrapher_count(char_map, 1, 1)
                print_search_results(result, "只有 1 位書法家的字")
            elif sub_choice == '2':
                result = filter_by_calligrapher_count(char_map, 2, 2)
                print_search_results(result, "2 位書法家都有的字")
            elif sub_choice == '3':
                result = filter_by_calligrapher_count(char_map, 3, 3)
                print_search_results(result, "3 位書法家都有的字")
            elif sub_choice == '4':
                result = filter_by_calligrapher_count(char_map, 4, 4)
                print_search_results(result, "4 位書法家都有的字（共有字）")
            elif sub_choice == '2+':
                result = filter_by_calligrapher_count(char_map, 2, 4)
                print_search_results(result, "2 位以上書法家有的字（可比對字）")
            elif sub_choice == '3+':
                result = filter_by_calligrapher_count(char_map, 3, 4)
                print_search_results(result, "3 位以上書法家有的字")
            else:
                print("[Error] 無效選項")

        elif choice == '2':
            print("\n搜尋常用字")
            print("  1: 前 100 個常用字")
            print("  2: 前 500 個常用字")
            print("  3: 前 1000 個常用字")
            print("  4: 所有常用字")

            sub_choice = input("\n請選擇: ").strip()

            if sub_choice == '1':
                result = filter_by_common_characters(char_map, 100)
                print_search_results(result, "前 100 個常用字（在字庫中）")
            elif sub_choice == '2':
                result = filter_by_common_characters(char_map, 500)
                print_search_results(result, "前 500 個常用字（在字庫中）")
            elif sub_choice == '3':
                result = filter_by_common_characters(char_map, 1000)
                print_search_results(result, "前 1000 個常用字（在字庫中）")
            elif sub_choice == '4':
                result = filter_by_common_characters(char_map, 10000)
                print_search_results(result, "所有常用字（在字庫中）")
            else:
                print("[Error] 無效選項")

        elif choice == '3':
            query = input("\n請輸入搜尋關鍵字（可以是單字或部首）: ").strip()
            if query:
                result = search_characters(char_map, query)
                print_search_results(result, f"包含「{query}」的字元")
            else:
                print("[Error] 請輸入關鍵字")

        elif choice == '4':
            # 顯示詳細統計
            print("\n" + "="*70)
            print(" 字庫詳細統計")
            print("="*70)

            print(f"\n 基本資訊:")
            print(f"   總字數: {stats['total_characters']}")
            print(f"   常用字: {stats['common_characters']} ({stats['common_percentage']:.1f}%)")

            print(f"\n 書法家分布:")
            for count in sorted(stats['by_calligrapher_count'].keys(), reverse=True):
                num = stats['by_calligrapher_count'][count]
                percentage = num / stats['total_characters'] * 100
                print(f"   {count} 位: {num:4d} 個字 ({percentage:5.1f}%)")

            # 常用字在各組的分布
            print(f"\n 常用字分布:")
            common_set = set(COMMON_CHARACTERS.replace('\n', ''))

            for count in sorted(stats['by_calligrapher_count'].keys(), reverse=True):
                chars_in_group = filter_by_calligrapher_count(char_map, count, count)
                common_in_group = sum(1 for c in chars_in_group if c in common_set)
                total_in_group = len(chars_in_group)
                if total_in_group > 0:
                    pct = common_in_group / total_in_group * 100
                    print(f"   {count} 位書法家: {common_in_group}/{total_in_group} ({pct:.1f}%)")

            print("\n" + "="*70)

        else:
            print("[Error] 無效選項")

        input("\n按 Enter 繼續...")


def main():
    """主程式"""
    interactive_search()


if __name__ == "__main__":
    main()
