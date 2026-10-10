"""Giữ app Streamlit Cloud không ngủ: mở bằng trình duyệt thật, bấm nút 'wake up' nếu app đang ngủ.
(Ping HTTP thuần KHÔNG đánh thức được Streamlit Cloud vì app cần phiên websocket.)
Chạy: APP_URLS="https://a.streamlit.app,https://b.onrender.com" python scripts/keepalive.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

URLS = [u.strip() for u in os.environ.get("APP_URLS", "").split(",") if u.strip()]


def main() -> int:
    if not URLS:
        print("Thiếu APP_URLS")
        return 1
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in URLS:
            page = browser.new_page()
            try:
                page.goto(url, timeout=90_000, wait_until="domcontentloaded")
                wake = page.get_by_role("button", name="get this app back up")
                if wake.count():
                    wake.first.click()
                    print(f"[WAKE] {url}")
                page.wait_for_timeout(20_000)  # đủ thời gian cho app khởi động & tạo session
                print(f"[OK] {url}")
            except Exception as exc:  # không dừng cả job vì 1 URL lỗi
                failed += 1
                print(f"[FAIL] {url}: {exc}")
            finally:
                page.close()
        browser.close()
    return 1 if failed == len(URLS) else 0


if __name__ == "__main__":
    sys.exit(main())
