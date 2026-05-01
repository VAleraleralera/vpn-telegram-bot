import os
import telebot
import requests
import json
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# === НАСТРОЙКИ 3X-UI ===
XUI_URL = os.environ.get("XUI_URL")
XUI_USERNAME = os.environ.get("XUI_USERNAME")
XUI_PASSWORD = os.environ.get("XUI_PASSWORD")

def create_vpn_key(expiry_days):
    try:
        session = requests.Session()
        session.verify = False
        login_resp = session.post(f"{XUI_URL}login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD})
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            return None
        inbounds_resp = session.get(f"{XUI_URL}panel/api/inbounds/list")
        inbounds = inbounds_resp.json().get("obj", [])
        inbound_id = None
        for inbound in inbounds:
            if inbound.get("protocol") == "vless":
                inbound_id = inbound.get("id")
                break
        if not inbound_id:
            return None
        expiry_time = int((datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000)
        payload = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": "",
                    "email": f"user_{int(time.time())}",
                    "expiryTime": expiry_time,
                    "totalGB": 0,
                    "enable": True
                }]
            })
        }
        add_resp = session.post(f"{XUI_URL}panel/api/inbounds/addClient", json=payload)
        if add_resp.status_code == 200 and add_resp.json().get("success"):
            return add_resp.json().get("obj", {}).get("url", "Ошибка: ссылка не получена")
        return None
    except Exception as e:
        print(f"Ошибка создания ключа: {e}")
        return None

# === КЛАВИАТУРЫ ===
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Тарифы", callback_data="tariffs"),
        InlineKeyboardButton("🔑 Купить", callback_data="buy"),
        InlineKeyboardButton("❓ Поддержка", callback_data="support"),
        InlineKeyboardButton("📢 Канал", callback_data="channel")
    )
    return keyboard

def tariff_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("1 месяц — 100 ₽", callback_data="tariff_1m"),
        InlineKeyboardButton("3 месяца — 900 ₽", callback_data="tariff_3m"),
        InlineKeyboardButton("6 месяцев — 1500 ₽", callback_data="tariff_6m"),
        InlineKeyboardButton("12 месяцев — 2500 ₽", callback_data="tariff_12m"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_main")
    )
    return keyboard

# === ОБРАБОТЧИКИ ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔹 *VPN Shop* 🔹\n\nВыберите действие:", parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    if call.data == "back_main":
        bot.edit_message_text("🔹 *VPN Shop* 🔹\n\nВыберите действие:", chat_id, msg_id, parse_mode="Markdown", reply_markup=main_menu())
    elif call.data == "tariffs":
        bot.edit_message_text("📅 *Выберите срок:*", chat_id, msg_id, parse_mode="Markdown", reply_markup=tariff_menu())
    elif call.data == "buy":
        bot.edit_message_text("📅 *Выберите срок:*", chat_id, msg_id, parse_mode="Markdown", reply_markup=tariff_menu())
    elif call.data == "support":
        bot.edit_message_text("🆘 *Поддержка*\n\nПо вопросам: @твой_ник", chat_id, msg_id, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="back_main")))
    elif call.data == "channel":
        bot.edit_message_text("📢 Канал: https://t.me/твой_канал", chat_id, msg_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="back_main")))
    elif call.data.startswith("tariff_"):
        days = {"tariff_1m": 30, "tariff_3m": 90, "tariff_6m": 180, "tariff_12m": 365}.get(call.data, 30)
        bot.edit_message_text(f"⏳ *Создаём ключ на {days} дней...*", chat_id, msg_id, parse_mode="Markdown")
        key = create_vpn_key(days)
        if key:
            bot.edit_message_text(f"✅ *Ваш ключ:*\n`{key}`\n\nПодключение: Hiddify / v2rayNG / Nekoray", chat_id, msg_id, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ В меню", callback_data="back_main")))
        else:
            bot.edit_message_text("❌ *Ошибка создания ключа.* Напишите админу.", chat_id, msg_id, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="back_main")))
    bot.answer_callback_query(call.id)

# === HTTP-сервер для Render ===
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
