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

# === ТВОИ НАСТРОЙКИ ===
TOKEN = "8703864624:AAGzkhvrv93U6k0a-6FNMz_ieeL8SQXQiVk"
XUI_URL = "https://72.56.119.147:54321/L7nSikoltRgG5CM2GC"
XUI_USERNAME = "VPn/Admin.log"
XUI_PASSWORD = "Vpn/AdMin.pas"

bot = telebot.TeleBot(TOKEN)

def get_inbound_id():
    try:
        sess = requests.Session()
        sess.verify = False
        login = sess.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD}, timeout=10)
        if login.status_code != 200 or not login.json().get("success"):
            return None
        resp = sess.get(f"{XUI_URL}/panel/api/inbounds/list", timeout=10)
        if resp.status_code != 200:
            return None
        for inbound in resp.json().get("obj", []):
            if inbound.get("protocol") == "vless":
                return inbound.get("id")
        return None
    except:
        return None

def create_vpn_key(days):
    inbound_id = get_inbound_id()
    if not inbound_id:
        return "❌ Ошибка: нет VLESS подключения в панели. Создайте его."

    sess = requests.Session()
    sess.verify = False
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
                # Получаем публичный ключ из Inbound
                public_key = ""
                try:
                    inb_resp = sess.get(f"{XUI_URL}/panel/api/inbounds/get/{inbound_id}", timeout=10)
                    if inb_resp.status_code == 200:
                        inb_data = inb_resp.json().get("obj", {})
                        stream = json.loads(inb_data.get("streamSettings", "{}"))
                        public_key = stream.get("realitySettings", {}).get("publicKey", "")
                except:
                    pass
                if not public_key:
                    public_key = "GEZbGybRfgK1eKGyZqBdnZEoVmsqQ0o6LSEItu6WQVE"
                # Собираем ссылку вручную
                host = XUI_URL.split("//")[1].split("/")[0]
                vless_link = f"vless://{client_id}@{host}:443?flow=xtls-rprx-vision&encryption=none&security=reality&sni=www.google.com&fp=chrome&pbk={public_key}&type=tcp&headerType=none#{email}"
                return vless_link
            else:
                return f"❌ Ошибка API: {data.get('msg')}"
        else:
            return f"❌ HTTP ошибка {resp.status_code}"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"

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

# === ВЕБ-СЕРВЕР ДЛЯ RENDER ===
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

print("✅ Бот запущен. Автовыдача активна.")
bot.infinity_polling()
