import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def download_wechat_images(url, output_folder="OUTPUT"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 模擬真實瀏覽器，避免被擋
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://mp.weixin.qq.com/"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 微信圖片通常在 <img> 標籤中，但網址在 data-src
        img_tags = soup.find_all("img")
        print(f"分析網頁中... 找到 {len(img_tags)} 個可能圖片標籤。")

        count = 0
        for img in img_tags:
            # 優先嘗試取得 data-src (微信專用)，若無則嘗試 data-original-src，最後才是 src
            img_url = img.get("data-src") or img.get("data-actualsrc") or img.get("src")
            
            if not img_url:
                continue

            # 確保是完整的網址
            img_url = urljoin(url, img_url)

            # 處理圖片格式：微信圖片網址有時沒副檔名，或在參數裡 (例如 ?wx_fmt=jpeg)
            # 我們從網址參數中抓取格式，若無則預設 jpg
            parsed_url = urlparse(img_url)
            query_params = dict(p.split('=') for p in parsed_url.query.split('&') if '=' in p)
            ext = query_params.get('wx_fmt', 'jpg')
            
            # 設定檔名
            
            filename = os.path.join(output_folder, f"image_{count + 1:02d}.{ext}")

            try:
                img_data = requests.get(img_url, headers=headers).content
                with open(filename, "wb") as f:
                    f.write(img_data)
                count += 1
                print(f"成功下載第 {count} 張: {filename}")
            except Exception as e:
                print(f"跳過圖片 {img_url}，原因: {e}")

        print(f"\n下載完成！共成功儲存 {count} 張圖片到 '{output_folder}' 資料夾。")

    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    # 你提供的網址
    target_url = "https://mp.weixin.qq.com/s/ZUV8yT4TFvdHJnON9LGx1Q"
    download_wechat_images(target_url)