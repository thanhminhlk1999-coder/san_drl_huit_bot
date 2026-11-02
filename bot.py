from datetime import datetime, timedelta, timezone
import html, json, os, random, re
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from playwright.sync_api import sync_playwright
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_CHAT_ID = "-1004460906077"

DEFAULT_USERS = {
    "default_admin": {
        "mssv": "2048289357",
        "name": "Phi Long Hoàng",
        "lop": "",
        "points": 70,
        "target": 90,
    }
}

CHAT_ID_FILE = "chat_id.txt"
HISTORY_FILE = "sent_history.json"
SOURCES_FILE = "extra_sources.json"
USERS_FILE = "registered_users.json"
OFFSET_FILE = "tele_offset.txt"

BASE_SOURCES = [
    "https://www.facebook.com/share/1d4om8AgtZ/?mibextid=wwXIfr",
    "https://www.facebook.com/share/19mXjzcQa6/?mibextid=wwXIfr",
    "https://www.facebook.com/share/1fnc3NYEe5/?mibextid=wwXIfr",
    "https://www.facebook.com/share/1GsxoSs736/?mibextid=wwXIfr",
    "https://www.facebook.com/share/1A8SkzAjfW/?mibextid=wwXIfr",
]

VN_TZ = timezone(timedelta(hours=7))


def now_vn():
    return datetime.now(VN_TZ).strftime("%H:%M:%S - %d/%m/%Y")


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


def send_tele(cid, text, buttons=None, thread_id=None):
    if not BOT_TOKEN:
        return
    reply_markup = {"inline_keyboard": buttons} if buttons else None
    payload = {
        "chat_id": cid,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if thread_id:
        payload["message_thread_id"] = thread_id
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json=payload,
        timeout=15,
    )


def handle_commands_once(cid, offset, history, users, extra_sources):
    try:
        res = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset + 1, "timeout": 4},
            timeout=10,
        ).json()
        for item in res.get("result", []):
            offset = max(offset, item.get("update_id", 0))
            msg_obj = (
                item.get("message")
                or item.get("channel_post")
                or item.get("edited_message")
                or {}
            )
            chat_id = str(msg_obj.get("chat", {}).get("id", ""))
            thread_id = msg_obj.get("message_thread_id")
            if chat_id.startswith("-"):
                cid = chat_id
                open(CHAT_ID_FILE, "w", encoding="utf-8").write(cid)

            text = (msg_obj.get("text") or "").strip()
            if not text or not cid:
                continue

            user_id = str(msg_obj.get("from", {}).get("id", "user"))
            cmd = text.split()[0].split("@")[0].lower()

            if cmd == "/reg":
                reg_content = re.sub(r"^/reg(@\w+)?\s*", "", text).strip()
                parts = reg_content.split(maxsplit=1)
                if len(parts) >= 1:
                    mssv = parts[0]
                    name = parts[1] if len(parts) > 1 else msg_obj.get("from", {}).get("first_name", "Sinh viên")
                    users[user_id] = {
                        "mssv": mssv,
                        "name": name,
                        "points": 70,
                        "target": 90
                    }
                    save_json(USERS_FILE, users)
                    send_tele(cid, f"✅ <b>Đăng ký thông tin thành công!</b>\n• MSSV: <code>{mssv}</code>\n• Họ tên: <b>{name}</b>", thread_id=thread_id)
                else:
                    send_tele(cid, "⚠️ Vui lòng nhập đúng cú pháp. Ví dụ: <code>/reg 2048289357 Phi Long Hoàng</code>", thread_id=thread_id)

            elif cmd == "/add":
                new_link = re.sub(r"^/add(@\w+)?\s*", "", text).strip()
                if new_link.startswith("http") and new_link not in extra_sources:
                    extra_sources.append(new_link)
                    save_json(SOURCES_FILE, extra_sources)
                    send_tele(cid, f"✅ <b>Đã thêm nguồn quét thành công!</b>\n🔗 <code>{new_link}</code>", thread_id=thread_id)
                else:
                    send_tele(cid, "⚠️ Vui lòng nhập đúng định dạng link. Ví dụ: <code>/add https://facebook.com/...</code>", thread_id=thread_id)

            elif cmd == "/latest":
                history_list = list(history)
                recent = history_list[-5:] if history_list else []
                if recent:
                    msg = "🗂 <b>CÁC BÀI ĐRL GẦN NHẤT:</b>\n━━━━━━━━━━━━━━━━━━━\n"
                    for idx, link in enumerate(recent, 1):
                        msg += f"{idx}️⃣ <a href='{link}'>Xem bài viết tại đây</a>\n"
                else:
                    msg = "🗂 <b>CÁC BÀI ĐRL GẦN NHẤT:</b>\nChưa ghi nhận bài viết nào trong lịch sử quét gần đây."
                send_tele(cid, msg, thread_id=thread_id)

        if offset > 0:
            open(OFFSET_FILE, "w", encoding="utf-8").write(str(offset))
    except Exception:
        pass
    return cid, offset


def main():
    history = set(load_json(HISTORY_FILE, []))
    extra_sources = load_json(SOURCES_FILE, [])
    if not isinstance(extra_sources, list):
        extra_sources = []
    users = load_json(USERS_FILE, DEFAULT_USERS.copy())
    save_json(USERS_FILE, users)

    cid = DEFAULT_CHAT_ID
    if os.path.exists(CHAT_ID_FILE):
        saved = open(CHAT_ID_FILE, "r", encoding="utf-8").read().strip()
        if saved:
            cid = saved

    offset = 0
    if os.path.exists(OFFSET_FILE):
        try:
            offset = int(open(OFFSET_FILE, "r", encoding="utf-8").read().strip())
        except Exception:
            offset = 0

    cid, offset = handle_commands_once(cid, offset, history, users, extra_sources)


if __name__ == "__main__":
    main()
