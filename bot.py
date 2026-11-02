from datetime import datetime, timedelta, timezone
import html, json, os, random, re
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from playwright.sync_api import sync_playwright
import requests

# ================= CẤU HÌNH AN TOÀN =================
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

BASE_KEYWORDS = [
    "điểm rèn luyện", "đrl", "cộng điểm", "link đăng ký", "form đăng ký",
    "hội thảo", "tọa đàm", "workshop", "cổ vũ", "tình nguyện", "tham gia",
    "sinh viên", "minigame", "học thuật", "chuyên đề", "cuộc thi", "điểm danh",
]

FORTUNES = [
    "🌟 <b>Đại Cát:</b> Nhân phẩm bùng nổ! Canh form nào dính form đó!",
    "🔥 <b>Thượng Cát:</b> Sắp có kèo thơm +5 ĐRL online, nhớ bật chuông nhóm!",
    "🍀 <b>Trung Cát:</b> Đường học vấn hanh thông, điểm rèn luyện tăng đều!",
    "⚡ <b>Tiểu Cát:</b> Cẩn thận ngủ quên giờ điểm danh chiều nay nhé!",
    "🎯 <b>Lời khuyên vũ trụ:</b> Chăm bấm nút Điền 1-Chạm, cuối kỳ auto Xuất Sắc!",
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


def ask_gemini_ai(prompt_text):
    if not GEMINI_API_KEY:
        return "⚠️ Chưa cấu hình GEMINI_API_KEY trong GitHub Secrets!"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    try:
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "⚠️ AI đang bận, vui lòng thử lại sau!"


def ai_summarize_drl_post(raw_text):
    if not GEMINI_API_KEY:
        return None
    prompt = (
        "Bạn là trợ lý săn Điểm Rèn Luyện cho sinh viên trường Đại học Công Thương TP.HCM (HUIT). "
        "Hãy đọc bài đăng sau và tóm tắt ngắn gọn trên 4 dòng (thuần văn bản, không dùng * hay #):\n"
        "- Tên hoạt động:\n- Quyền lợi (Số điểm ĐRL):\n- Thời gian & Hạn đăng ký:\n- Hình thức & Địa điểm:\n\n"
        f"Nội dung:\n{raw_text[:1500]}"
    )
    res = ask_gemini_ai(prompt)
    return res if (res and not res.startswith("⚠️")) else None


def get_rank_badge(pts):
    if pts >= 90:
        return "👑 Trùm Cuối Học Bổng (Xuất Sắc)"
    if pts >= 80:
        return "🔥 Chiến Thần Rèn Luyện (Tốt)"
    if pts >= 65:
        return "⚡ Thợ Săn Phong Trào (Khá)"
    if pts >= 50:
        return "🛡️ Sinh Viên Vượt Khó (TB)"
    return "🌱 Tân Binh Đang Gom Điểm"


def make_progress_bar(current, target=100):
    pct = min(max(int((current / max(target, 1)) * 10), 0), 10)
    return "🟩" * pct + "⬜" * (10 - pct)


def send_tele(cid, text, buttons=None, photo_url=None, thread_id=None):
    if not BOT_TOKEN:
        return
    reply_markup = {"inline_keyboard": buttons} if buttons else None
    if photo_url:
        payload = {
            "chat_id": cid,
            "photo": photo_url,
            "caption": text[:1020],
            "parse_mode": "HTML",
        }
        if thread_id:
            payload["message_thread_id"] = thread_id
        if reply_markup:
            payload["reply_markup"] = reply_markup
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            json=payload,
            timeout=15,
        )
        if r.status_code == 200:
            return
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


def set_bot_commands_menu():
    cmds = [
        {"command": "menu", "description": "📋 Mở bảng điều khiển & hướng dẫn"},
        {"command": "ai", "description": "🤖 Hỏi trợ lý AI (VD: /ai câu hỏi)"},
        {"command": "reg", "description": "✍️ Đăng ký: /reg MSSV - Họ Tên - Lớp"},
        {"command": "cong", "description": "➕ Cộng điểm ĐRL (VD: /cong 5)"},
        {"command": "bxh", "description": "🏆 Xem Bảng Xếp Hạng ĐRL của nhóm"},
        {"command": "gieoque", "description": "🔮 Gieo quẻ nhân phẩm săn ĐRL"},
        {"command": "latest", "description": "🗂 Xem 3 bài ĐRL mới nhất"},
        {"command": "status", "description": "🟢 Kiểm tra trạng thái hệ thống"},
    ]
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands",
            json={"commands": cmds},
            timeout=8,
        )
    except Exception:
        pass


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
            sender = msg_obj.get("from", {})
            uid = str(sender.get("id", ""))
            first_name = sender.get("first_name", "Phi Long Hoàng")
            if not text or not cid:
                continue

            cmd = text.split()[0].split("@")[0].lower()

            if cmd in ["/menu", "/help", "/start"]:
                send_tele(
                    cid,
                    "🤖 <b>TRUNG TÂM ĐIỀU KHIỂN BOT SĂN ĐRL HUIT (AI PRO)</b>\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "🧠 <b>1. Trợ lý AI Gemini:</b>\n"
                    "• <code>/ai [câu hỏi]</code> : Hỏi đáp AI mọi chủ đề\n\n"
                    "👤 <b>2. Điền Form 1-Chạm:</b>\n"
                    "• <code>/reg MSSV - Họ Tên - Lớp</code> : Tạo nút riêng\n\n"
                    "🏆 <b>3. Đua Top Điểm Rèn Luyện:</b>\n"
                    "• <code>/cong 5</code> : Cộng điểm sau khi điền form\n"
                    "• <code>/bxh</code> : Xem Bảng Xếp Hạng nhóm\n"
                    "• <code>/gieoque</code> : Xin quẻ may mắn hôm nay",
                    thread_id=thread_id,
                )

            elif cmd == "/ai":
                question = re.sub(r"^/ai(@\w+)?\s*", "", text).strip()
                if not question:
                    send_tele(
                        cid,
                        "🤖 Hãy gõ: <code>/ai câu hỏi của bạn</code>",
                        thread_id=thread_id,
                    )
                else:
                    ans = ask_gemini_ai(
                        f"Trả lời ngắn gọn, thân thiện cho sinh viên HUIT: {question}"
                    )
                    send_tele(
                        cid,
                        f"🤖 <b>TRỢ LÝ AI HUIT:</b>\n━━━━━━━━━━━━━━━━━━━\n{html.escape(ans)}",
                        thread_id=thread_id,
                    )

            elif cmd == "/reg":
                raw_info = re.sub(r"^/reg(@\w+)?\s*", "", text).strip()
                parts = [p.strip() for p in raw_info.split("-")]
                if len(parts) >= 2:
                    mssv, name = parts[0], parts[1]
                    lop = parts[2] if len(parts) >= 3 else ""
                    if mssv == "2048289357" and "default_admin" in users:
                        del users["default_admin"]
                    old_pts = users.get(uid, {}).get("points", 70)
                    users[uid] = {
                        "mssv": mssv,
                        "name": name,
                        "lop": lop,
                        "points": old_pts,
                        "target": 90,
                    }
                    save_json(USERS_FILE, users)
                    send_tele(
                        cid,
                        f"🎉 <b>ĐĂNG KÝ THÀNH CÔNG!</b>\n👤 <b>{html.escape(name)}</b> (<code>{html.escape(mssv)}</code>)",
                        thread_id=thread_id,
                    )

            elif cmd in ["/cong", "/checkin"]:
                target_uid = uid if uid in users else "default_admin"
                if target_uid not in users:
                    users[uid] = {
                        "mssv": "2048289357",
                        "name": "Phi Long Hoàng",
                        "lop": "",
                        "points": 70,
                        "target": 90,
                    }
                    target_uid = uid
                m_num = re.search(r"(-?\d+)", text)
                add_pts = int(m_num.group(1)) if m_num else 3
                users[target_uid]["points"] = min(
                    max(users[target_uid].get("points", 70) + add_pts, 0), 100
                )
                cur = users[target_uid]["points"]
                save_json(USERS_FILE, users)
                send_tele(
                    cid,
                    f"⚡ <b>CẬP NHẬT ĐRL:</b> {html.escape(users[target_uid]['name'])}\n"
                    f"📊 <b>Tổng điểm:</b> <b>{cur}</b>/90đ (+{add_pts}đ)\n"
                    f"{make_progress_bar(cur, 90)}\n"
                    f"🎖 {get_rank_badge(cur)}",
                    thread_id=thread_id,
                )

            elif cmd == "/bxh":
                sorted_u = sorted(
                    users.values(), key=lambda x: x.get("points", 70), reverse=True
                )
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
                lines = [
                    f"{medals[i] if i < 8 else '🔹'} <b>{html.escape(u['name'])}</b> (<code>{html.escape(u['mssv'])}</code>) — <b>{u.get('points', 70)}đ</b>\n    └ {get_rank_badge(u.get('points', 70))}"
                    for i, u in enumerate(sorted_u[:8])
                ]
                send_tele(
                    cid,
                    "🏆 <b>BẢNG XẾP HẠNG ĐRL HUIT</b>\n━━━━━━━━━━━━━━━━━━━\n"
                    + "\n\n".join(lines),
                    thread_id=thread_id,
                )

            elif cmd == "/gieoque":
                send_tele(
                    cid,
                    f"🔮 <b>QUẺ BÓI CHO {html.escape(first_name.upper())}:</b>\n{random.choice(FORTUNES)}\n🎲 <b>Số may mắn:</b> <code>{random.randint(1, 99)}</code>",
                    thread_id=thread_id,
                )

            elif cmd == "/status":
                send_tele(
                    cid,
                    f"🟢 <b>BOT ĐANG HOẠT ĐỘNG AN TOÀN!</b>\n⏱ {now_vn()}\n🗂 Đã lưu: {len(history)} bài",
                    thread_id=thread_id,
                )

        if offset > 0:
            open(OFFSET_FILE, "w", encoding="utf-8").write(str(offset))
    except Exception:
        pass
    return cid, offset


def inspect_google_form(url):
    try:
        r = requests.get(url, timeout=8, allow_redirects=True)
        final_url = r.url
        if "docs.google.com/forms" not in final_url:
            return final_url, {}
        m = re.search(
            r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);\s*</script>", r.text, re.DOTALL
        )
        if not m:
            return final_url, {}
        data = json.loads(m.group(1))
        items = data[1][1] if len(data) > 1 and len(data[1]) > 1 else []
        field_map = {}
        for item in items:
            if not isinstance(item, list) or len(item) < 5:
                continue
            title = str(item[1] or "").lower()
            q_data = item[4]
            if isinstance(q_data, list) and len(q_data) > 0 and isinstance(q_data[0], list):
                entry_id = f"entry.{q_data[0][0]}"
                if any(k in title for k in ["mssv", "mã số", "mã sinh viên", "masv"]):
                    field_map["mssv"] = entry_id
                elif any(k in title for k in ["họ và tên", "họ tên", "tên sinh viên", "full name"]):
                    field_map["name"] = entry_id
                elif any(k in title for k in ["lớp", "mã lớp", "chi đoàn"]):
                    field_map["lop"] = entry_id
        return final_url, field_map
    except Exception:
        return url, {}


def make_user_prefill_url(base_form_url, field_map, user_profile):
    params = {}
    if "mssv" in field_map and user_profile.get("mssv"):
        params[field_map["mssv"]] = user_profile["mssv"]
    if "name" in field_map and user_profile.get("name"):
        params[field_map["name"]] = user_profile["name"]
    if "lop" in field_map and user_profile.get("lop"):
        params[field_map["lop"]] = user_profile["lop"]
    if not params:
        return base_form_url
    return f"{base_form_url.split('?')[0]}?usp=pp_url&{urlencode(params)}"


def extract_links(raw_links, text):
    domains = [
        "forms.gle", "docs.google.com/forms", "forms.office.com",
        "bit.ly", "tinyurl.com", "linktr.ee", "shorturl.at",
    ]
    found = []
    for l in raw_links:
        if "facebook.com/l.php" in l:
            l = unquote(parse_qs(urlparse(l).query).get("u", [l])[0])
        if any(d in l.lower() for d in domains):
            found.append(l)
    pat = r"https?://(?:forms\.gle|docs\.google\.com/forms|forms\.office\.com|bit\.ly|tinyurl\.com|linktr\.ee|shorturl\.at)/[^\s\"'<>)\]]+"
    found.extend(re.findall(pat, text))
    return list(dict.fromkeys(found))


def main():
    if not os.path.exists(HISTORY_FILE):
        set_bot_commands_menu()
    history = set(load_json(HISTORY_FILE, []))
    extra_sources = load_json(SOURCES_FILE, [])
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

    # 1. Xử lý các lệnh Telegram đang chờ
    cid, offset = handle_commands_once(cid, offset, history, users, extra_sources)

    # 2. Quét nhanh 5 trang Facebook (chỉ mất ~25 giây rồi nghỉ, an toàn 100%)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="vi-VN").new_page()
        for url in BASE_SOURCES + extra_sources:
            try:
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                page.mouse.wheel(0, 650)
                page.wait_for_timeout(800)

                for post in page.locator("div[role='article']").all()[:4]:
                    text = post.inner_text().strip()
                    key = re.sub(r"\s+", " ", text)[:120]
                    if len(text) >= 40 and key not in history:
                        if any(kw in text.lower() for kw in BASE_KEYWORDS):
                            raw = [a.get_attribute("href") or "" for a in post.locator("a").all()]
                            links = extract_links(raw, text)
                            ai_summary = ai_summarize_drl_post(text)

                            btns = []
                            for i, l in enumerate(links, 1):
                                final_url, field_map = inspect_google_form(l)
                                btns.append([{"text": f"📝 Mở Form Gốc #{i}", "url": final_url}])
                                if field_map and users:
                                    row = []
                                    for u in list(users.values())[:6]:
                                        u_url = make_user_prefill_url(final_url, field_map, u)
                                        row.append({"text": f"⚡ {u['name'].split()[-1]} ({u['mssv'][-3:]})", "url": u_url})
                                        if len(row) == 2:
                                            btns.append(row)
                                            row = []
                                    if row:
                                        btns.append(row)

                            body = f"🧠 <b>AI Tóm tắt:</b>\n{html.escape(ai_summary)}\n" if ai_summary else f"📝 {html.escape(text[:280])}...\n"
                            msg = f"🚨 <b>PHÁT HIỆN KÈO ĐRL MỚI!</b>\n━━━━━━━━━━━━━━━━━━━\n{body}"
                            send_tele(cid, msg, btns)
                            history.add(key)
            except Exception:
                pass
        browser.close()

    save_json(HISTORY_FILE, list(history)[-500:])


if __name__ == "__main__":
    main()
