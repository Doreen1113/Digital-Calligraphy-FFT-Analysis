"""自動錄製 demo 影片（Playwright，1280×720 webm）。

依 docs/demo_script.md 的分鏡自動操作瀏覽器並錄影：
project page 捲動 → 互動滑桿 → 診斷結果 → 平台求字。
產出無聲畫面，旁白依腳本另行配音。

前置：平台在 8123、project page 靜態伺服器在 8124。
用法：python tools/record_demo.py [--out demo_out]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PLATFORM = "http://127.0.0.1:8123"
PAGE = "http://127.0.0.1:8124"
W, H = 1280, 720


def smooth_scroll(page, to: int, duration: float = 2.0, steps: int = 40):
    """以固定步幅平滑捲動到指定位置，避免瞬移。"""
    cur = page.evaluate("window.scrollY")
    for i in range(1, steps + 1):
        page.evaluate(f"window.scrollTo(0, {cur + (to - cur) * i / steps})")
        time.sleep(duration / steps)


def scroll_to_selector(page, sel: str, duration: float = 2.0, offset: int = -80):
    y = page.evaluate(
        f"() => {{ const e = document.querySelector({sel!r});"
        f" return e ? e.getBoundingClientRect().top + window.scrollY + {offset} : null; }}")
    if y is None:
        print(f"  [warn] 找不到 {sel}")
        return
    smooth_scroll(page, int(y), duration)


def drag_slider(page, sel: str, frm: int, to: int, hold: float = 0.35):
    """逐格拖動 range slider，每格停留讓觀眾看清變化。"""
    el = page.locator(sel)
    el.scroll_into_view_if_needed()
    box = el.bounding_box()
    if not box:
        return
    n_min = int(el.get_attribute("min") or 0)
    n_max = int(el.get_attribute("max") or 8)
    def x_at(v):
        return box["x"] + box["width"] * (v - n_min) / max(1, (n_max - n_min))
    y = box["y"] + box["height"] / 2
    page.mouse.move(x_at(frm), y)
    page.mouse.down()
    step = 1 if to >= frm else -1
    for v in range(frm, to + step, step):
        page.mouse.move(x_at(v), y, steps=6)
        time.sleep(hold)
    page.mouse.up()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo_out")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-device-scale-factor=1", "--hide-scrollbars"])
        ctx = browser.new_context(viewport={"width": W, "height": H},
                                  record_video_dir=str(out),
                                  record_video_size={"width": W, "height": H},
                                  device_scale_factor=1)
        page = ctx.new_page()

        # ── 0:00 開場：project page 標題 → 傅立葉重建圖 ──
        print("[0:00] 開場")
        page.goto(PAGE, wait_until="networkidle")
        time.sleep(4.0)
        scroll_to_selector(page, "figure", 3.0)
        time.sleep(6.0)

        # ── 0:20 資料集：同字對照牆 ──
        print("[0:20] 資料集")
        scroll_to_selector(page, ".facts", 2.5)
        time.sleep(4.0)
        scroll_to_selector(page, "img[alt*='道、人、月、學']", 2.5)
        time.sleep(7.0)

        # ── 0:50 核心：互動滑桿 ──
        print("[0:50] 互動滑桿")
        scroll_to_selector(page, ".demo", 2.0, offset=-60)
        time.sleep(1.5)
        drag_slider(page, "#lpRange", 0, 4, hold=0.5)     # 2% → 10%
        time.sleep(5.0)                                    # 停在 10%，讓 94.7% 被看見
        drag_slider(page, "#lpRange", 4, 8, hold=0.35)    # 10% → 100%
        time.sleep(1.5)
        drag_slider(page, "#lpRange", 8, 0, hold=0.18)    # 拉回
        time.sleep(1.0)
        # 換一個字再演示一次
        page.locator(".demo-chars button[data-k='liu_xian']").click()
        time.sleep(0.8)
        drag_slider(page, "#lpRange", 0, 4, hold=0.5)
        time.sleep(4.0)

        # ── 1:25 誠實的科學：跨資料集表格 → 結構鴻溝圖 ──
        print("[1:25] 跨資料集與結構鴻溝")
        scroll_to_selector(page, "table", 2.5, offset=-120)
        time.sleep(4.0)
        scroll_to_selector(page, "img[alt*='生成結果與標準字']", 3.0, offset=-100)
        time.sleep(7.0)

        # ── 1:50 平台求字 ──
        print("[1:50] 平台求字")
        page.goto(f"{PLATFORM}/generate", wait_until="networkidle")
        time.sleep(2.0)
        page.fill("#txt", "")
        for ch in "寧靜致遠":
            page.type("#txt", ch, delay=180)
        time.sleep(0.6)
        page.select_option("#cal", "趙孟頫")
        time.sleep(0.8)
        page.click("#go")
        page.wait_for_timeout(2500)
        time.sleep(2.0)
        page.evaluate("document.querySelector('.paper').scrollIntoView({block:'center'})")
        time.sleep(4.0)
        # 點一個 AI 補的字，展示右側候選面板
        cells = page.locator(".cell")
        if cells.count() > 0:
            cells.nth(0).click()
            time.sleep(5.0)

        # ── 2:20 收尾：回到 project page 標題 ──
        print("[2:20] 收尾")
        page.goto(PAGE, wait_until="networkidle")
        time.sleep(5.0)

        video = page.video
        ctx.close()
        browser.close()
        if video:
            path = Path(video.path())
            final = out / "demo.webm"
            if path.exists():
                path.rename(final)
                print(f"\n完成：{final}　({final.stat().st_size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
