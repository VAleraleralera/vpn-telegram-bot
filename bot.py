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
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = os.environ.get("BOT_TOKEN")
XUI_URL = "https://72.56.119.147:54321/L7nSikoltRgG5CM2GC"
XUI_USERNAME = "VPn/Admin.log"
XUI_PASSWORD = "Vpn/AdMin.pas"

bot = telebot.TeleBot(TOKEN)

def get_inbound_id():
    session = requests.Session()
    session.verify = False
    resp = session.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD})
    if resp.status_code != 200 or not resp.json().get("success"):
        return None
    inbounds_resp = session.get(f"{XUI_URL}/panel/api/inbounds/list")
    if inbounds_resp.status_code != 200:
        return None
    for inbound in inbounds_resp.json().get("obj", []):
        if inbound.get("protocol") == "vless":
            return inbound.get("id")
    return None

def create_vpn_key(days):
    inbound_id = get_inbound_id()
    if not inbound_id:
        return "❌ VLESS inbound не найден. Создайте его в панели."
    
    session = requests.Session()
    session.verify = False
    session.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD})
    
    expiry_time = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
    client_id = str(uuid.uuid4())
    email = f"user_{int(time.time())}"
    
    payload = {
        "id": inbound_id,
        "settings": json.dumps({
            "clients": [{
                "id": client_id,
                "email": email,
                "expiryTime": expiry_time,
                "totalGB": 0,
                "enable": True
            }]
        })
    }
    
    resp = session.post(f"{XUI_URL}/panel/api/inbounds/addClient", json=payload)
    if resp.status_code == 200:
        result = resp.json()
        if result.get("success"):
            return result.get("obj", {}).get("url")
        else:
            return f"❌ Ошибка API: {result.get('msg')}"
    return f"❌ Ошибка HTTP: {resp.status_code}"

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
    bot.edit_message_text(f"⏳ *Создаём ключ на {days} дней...*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    key = create_vpn_key(days)
    if key and key.startswith("vless://"):
        bot.edit_message_text(f"✅ *Ваш ключ:*\n`{key}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text(f"❌ {key}", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ========== HTTP-сервер для Render ==========
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

print("✅ Бот запущен. Автовыдача активна")
bot.infinity_polling()
