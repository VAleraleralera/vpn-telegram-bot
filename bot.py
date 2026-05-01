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
XUI_URL = "https://72.56.119.147:8443/L7nSikoltRgG5CM2GC"
XUI_USERNAME = "VPn/Admin.log"
XUI_PASSWORD = "Vpn/AdMin.pas"
PUBLIC_KEY = "GEZbGybRfgK1eKGyZqBdnZEoVmsqQ0o6LSEItu6WQVE"

bot = telebot.TeleBot(TOKEN)

# ========== ПОЛУЧАЕМ ID И ПОРТ VLESS INBOUND ==========
def get_inbound_info():
    try:
        sess = requests.Session()
        sess.verify = False
        login = sess.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD}, timeout=10)
        if login.status_code != 200 or not login.json().get("success"):
            return None, None
        resp = sess.get(f"{XUI_URL}/panel/api/inbounds/list", timeout=10)
        if resp.status_code != 200:
            return None, None
        for inbound in resp.json().get("obj", []):
            if inbound.get("protocol") == "vless":
                inbound_id = inbound.get("id")
                port = inbound.get("port")
                print(f"Найден Inbound ID: {inbound_id}, порт: {port}")
                return inbound_id, port
        return None, None
    except Exception as e:
        print(f"Ошибка get_inbound_info: {e}")
        return None, None

# ========== СОЗДАНИЕ КЛЮЧА С АВТОМАТИЧЕСКИМ ПОРТОМ ==========
def create_vpn_key(days):
    inbound_id, port = get_inbound_info()
    if not inbound_id:
        return "❌ Ошибка: VLESS Inbound не найден. Создайте его в панели."

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
                # Получаем хост из XUI_URL (без порта)
                host = XUI_URL.split("//")[1].split("/")[0].split(":")[0]
                vless_link = f"vless://{client_id}@{host}:{port}?flow=xtls-rprx-vision&encryption=none&security=reality&sni=www.google.com&fp=chrome&pbk={PUBLIC_KEY}&type=tcp&headerType=none#{email}"
                return vless_link
            else:
                return f"❌ Ошибка API: {data.get('msg')}"
        else:
            return f"❌ HTTP ошибка {resp.status_code}"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"

# ========== КНОПКИ ==========
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

print("✅ Бот запущен. Автоматическое определение порта активно.")
bot.infinity_polling()
