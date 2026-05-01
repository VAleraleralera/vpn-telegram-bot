import os
import telebot
import subprocess
import json
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN")
XUI_URL = os.environ.get("XUI_URL")
XUI_USERNAME = os.environ.get("XUI_USERNAME")
XUI_PASSWORD = os.environ.get("XUI_PASSWORD")

bot = telebot.TeleBot(TOKEN)

def run_curl(url, data=None):
    cmd = ["curl", "-s", "-k", "-X", "POST", url, "-H", "Content-Type: application/json"]
    if data:
        cmd += ["-d", json.dumps(data)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def get_inbound_id():
    login_data = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    login_resp = run_curl(f"{XUI_URL}/login", login_data)
    if not login_resp:
        return None
    # дальше — получаем список inbound
    raw = run_curl(f"{XUI_URL}/panel/api/inbounds/list")
    try:
        inbounds = json.loads(raw).get("obj", [])
        for inbound in inbounds:
            if inbound.get("protocol") == "vless":
                return inbound.get("id")
    except:
        return None
    return None

def create_vpn_key(days):
    inbound_id = get_inbound_id()
    if not inbound_id:
        return None
    expiry = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
    email = f"user_{int(datetime.now().timestamp())}"
    client_data = {
        "id": inbound_id,
        "settings": json.dumps({
            "clients": [{
                "id": "",
                "email": email,
                "expiryTime": expiry,
                "totalGB": 0,
                "enable": True
            }]
        })
    }
    resp = run_curl(f"{XUI_URL}/panel/api/inbounds/addClient", client_data)
    try:
        return json.loads(resp).get("obj", {}).get("url")
    except:
        return None

# ------------------ Твои обычные хендлеры бота ------------------
def tariff_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("1 месяц — 350 ₽", callback_data="30"),
        InlineKeyboardButton("3 месяца — 900 ₽", callback_data="90"),
        InlineKeyboardButton("6 месяцев — 1500 ₽", callback_data="180"),
        InlineKeyboardButton("12 месяцев — 2500 ₽", callback_data="365")
    )
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔹 Выбери тариф:", reply_markup=tariff_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    days = int(call.data)
    bot.edit_message_text(f"⏳ Создаю ключ на {days} дней...", call.message.chat.id, call.message.message_id)
    key = create_vpn_key(days)
    if key:
        bot.edit_message_text(f"✅ Твой ключ:\n`{key}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ Ошибка генерации. Попробуй позже.", call.message.chat.id, call.message.message_id)

# ------------------ Веб-сервер для Render ------------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

Thread(target=run_http_server, daemon=True).start()

print("✅ Бот запущен")
bot.infinity_polling()
