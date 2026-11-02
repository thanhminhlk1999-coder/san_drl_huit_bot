from datetime import datetime, timedelta, timezone
import json, os
from playwright.sync_api import sync_playwright
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DEFAULT_CHAT_ID = "-1004460906077"

CHAT_ID_FILE = "chat_id.txt"
HISTORY_FILE = "sent_history.json"
SOURCES_FILE = "extra_sources.json"

BASE_SOURCES = [
    "https://www.facebook.com/share/1d4om8AgtZ/?mibextid=wwXIfr",
    "https://www.facebook.com/share/19mXjzcQa6/?mibextid=wwXIfr",
    "https://www.facebook.com/share/1fnc3NYEe5/?mibextid=wwXIfr",
    "https://www.facebook.com/share/1GsxoSs736/?mibextid=wwXIfr",
    "https://www.facebook.com/share/1A8SkzAjfW/?mibextid=wwXIfr",
]

BASE_KEYWORDS = [
    "điểm rèn luyện", "đrl", "cộng điểm", "link đăng ký", "form đăng ký",
    "hội thảo", "tọa đàm", "workshop", "cổ vũ", "tình nguyện", "tham gia",
    "sinh viên", "minigame", "học thuật", "chuyên đề", "cuộc thi", "điểm danh",
]

def load_json(path, default):
    if os.path.exists(path):
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
            if data:
                return data
        except Exception:
            pass
    return default

def save_json(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)

def send_tele(cid, text):
    if not BOT_TOKEN:
        return
    payload = {
        "chat_id": cid,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=15)

def main():
    history = set(load_json(HISTORY_FILE, []))
    extra_sources = load_json(SOURCES_FILE, [])
    if not isinstance(extra_sources, list):
        extra_sources = []
        
    all_sources = BASE_SOURCES + extra_sources
    
    cid = DEFAULT_CHAT_ID
    if os.path.exists(CHAT_ID_FILE):
        saved = open(CHAT_ID_FILE, "r", encoding="utf-8").read().strip()
        if saved:
            cid = saved

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="vi-VN").new_page()
        
        for url in all_sources:
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                posts = page.locator("article, div[role='article']").all()
                for post in posts[:5]:
                    text_content = post.inner_text().lower()
                    if any(kw in text_content for kw in BASE_KEYWORDS):
                        links = post.locator("a[href*='/posts/'], a[href*='/permalink/'], a[href*='story.php']").all()
                        for link in links:
                            href = link.get_attribute("href")
                            if href:
                                clean_link = href.split("?")[0]
                                if clean_link not in history:
                                    history.add(clean_link)
                                    msg = f"🔥 <b>PHÁT HIỆN KÈO ĐIỂM RÈN LUYỆN MỚI!</b>\n━━━━━━━━━━━━━━━━━━━\n🔗 <a href='{clean_link}'>Bấm vào đây để xem chi tiết bài viết</a>"
                                    send_tele(cid, msg)
                                    break
            except Exception:
                pass
        browser.close()

    save_json(HISTORY_FILE, list(history)[-200:])

if __name__ == "__main__":
    main()
