import os
import telebot
import requests
import json
import time
import uuid
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== ТВОИ ДАННЫЕ ==========
TOKEN = "8703864624:AAGzkhvrv93U6k0a-6FNMz_ieeL8SQXQiVk"
XUI_URL = "http://72.56.119.147:8443/L7nSikoltRgG5CM2GC"   # ← ТУТ HTTP, НЕ HTTPS
XUI_USERNAME = "VPn/Admin.log"
XUI_PASSWORD = "Vpn/AdMin.pas"
PUBLIC_KEY = "GEZbGybRfgK1eKGyZqBdnZEoVmsqQ0o6LSEItu6WQVE"

bot = telebot.TeleBot(TOKEN)

def get_inbound_info():
    try:
        sess = requests.Session()
        login_resp = sess.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD}, timeout=10)
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            print("Login failed")
            return None, None
        resp = sess.get(f"{XUI_URL}/panel/api/inbounds/list", timeout=10)
        if resp.status_code != 200:
            print(f"Failed to get inbounds: {resp.status_code}")
            return None, None
        data = resp.json()
        for inbound in data.get("obj", []):
            if inbound.get("protocol", "").lower() == "vless":
                return inbound.get("id"), inbound.get("port")
        return None, None
    except Exception as e:
        print(f"get_inbound_info error: {e}")
        return None, None

def create_vpn_key(days):
    inbound_id, port = get_inbound_info()
    if not inbound_id:
        return "❌ Ошибка: VLESS Inbound не найден."

    sess = requests.Session()
    sess.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD}, timeout=10)
    expiry = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
    client_id = str(uuid.uuid4())
    email = f"user_{int(time.time())}"
    payload = {
        "id": inbound_id,
        "settings": json.dumps({
            "clients": [{
                "id": client_id,
                "email": email,
                "expiryTime": expiry,
                "totalGB": 0,
                "enable": True
            }]
        })
    }
    try:
        resp = sess.post(f"{XUI_URL}/panel/api/inbounds/addClient", json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                host = XUI_URL.split("//")[1].split("/")[0].split(":")[0]
                return f"vless://{client_id}@{host}:{port}?flow=xtls-rprx-vision&encryption=none&security=reality&sni=www.google.com&fp=chrome&pbk={PUBLIC_KEY}&type=tcp&headerType=none#{email}"
            else:
                return f"❌ Ошибка: {data.get('msg')}"
        else:
            return f"❌ HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

def tariff_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📱 1 месяц — 350 ₽", callback_data="30"),
        InlineKeyboardButton("🎮 3 месяца — 900 ₽", callback_data="90"),
        InlineKeyboardButton("⭐️ 6 месяцев — 1500 ₽", callback_data="180"),
        InlineKeyboardButton("🔥 12 месяцев — 2500 ₽", callback_data="365")
    )
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔹 *VPN Shop* 🔹\nВыбери тариф:", parse_mode="Markdown", reply_markup=tariff_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    days = int(call.data)
    bot.edit_message_text(f"⏳ *Создаю ключ на {days} дней...*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    key = create_vpn_key(days)
    if key.startswith("vless://"):
        bot.edit_message_text(f"✅ *Ваш ключ:*\n`{key}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text(key, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

Thread(target=run_http_server, daemon=True).start()

print("✅ Бот запущен. HTTP режим.")
bot.infinity_polling()
