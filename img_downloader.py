import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

def download_wechat_images_final(url, output_folder="10"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    options = Options()
    # 注意：暫時關閉無頭模式(Headless)，讓你看看瀏覽器在做什麼
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)

    # 隱藏自動化特徵
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        print(f"正在啟動瀏覽器...")
        driver.get(url)

        # 等待 5 秒讓內容跑出來，如果看到驗證碼請手動點一下
        time.sleep(5) 

        # 模擬捲動
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        content_area = soup.find('div', id='js_content')
        
        if not content_area:
            print("依舊找不到內容，請檢查彈出的瀏覽器視窗是否顯示正常。")
            return

        img_tags = content_area.find_all("img")
        print(f"成功解析！找到 {len(img_tags)} 個圖片標籤。")

        headers = {"Referer": "https://mp.weixin.qq.com/"}
        count = 0
        for img in img_tags:
            img_url = img.get("data-src") or img.get("src")
            if not img_url or "mmbiz.qpic.cn" not in img_url:
                continue

            # 抓取格式
            params = parse_qs(urlparse(img_url).query)
            ext = params.get('wx_fmt', ['jpg'])[0]
            filename = os.path.join(output_folder, f"image_{count + 1:02d}.{ext}")

            img_data = requests.get(img_url, headers=headers).content
            with open(filename, "wb") as f:
                f.write(img_data)
            count += 1
            print(f"已下載: {filename}")

        print(f"\n任務完成！共存儲 {count} 張圖片。")

    finally:
        driver.quit()

if __name__ == "__main__":
    # === 網址打在這裡 ===
    my_url = "https://mp.weixin.qq.com/s?__biz=Mzg4NTczNjg2NA%3D%3D&mid=2247515484&idx=1&sn=6879c01bfd9f248ca2ccf4be5ed7d47c&source=41&scene=21&poc_token=HG7lqGmjO9il7HYxXx8A6Lnl1L85_Y6wTJeoEAMC" 
    # ==================
    download_wechat_images_final(my_url)