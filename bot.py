import os
import telebot
import requests
import json
import time
from datetime import datetime, timedelta
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ =====
TOKEN = os.environ.get("BOT_TOKEN")
XUI_URL = os.environ.get("XUI_URL")
XUI_USERNAME = os.environ.get("XUI_USERNAME")
XUI_PASSWORD = os.environ.get("XUI_PASSWORD")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

bot = telebot.TeleBot(TOKEN)

# ===== ФУНКЦИЯ ДЛЯ СОЗДАНИЯ INBOUND (ЕСЛИ ЕГО НЕТ) =====
def ensure_inbound_exists():
    """Проверяет наличие VLESS Inbound и создаёт его при необходимости"""
    session = requests.Session()
    session.verify = False
    session.headers.update({"Content-Type": "application/json"})
    
    # Логинимся
    login_payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        login_resp = session.post(f"{XUI_URL}login", json=login_payload, timeout=10)
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            return None, "❌ Ошибка логина в панель"
    except Exception as e:
        return None, f"❌ Ошибка соединения: {e}"
    
    # Получаем список Inbound
    resp = session.get(f"{XUI_URL}panel/api/inbounds/list", timeout=10)
    if resp.status_code != 200:
        return None, f"❌ Ошибка получения списка: {resp.status_code}"
    
    inbounds = resp.json().get("obj", [])
    
    # Ищем VLESS Inbound
    for inbound in inbounds:
        if inbound.get("protocol") == "vless":
            return inbound.get("id"), None  # Нашли, возвращаем ID
    
    # Если не нашли — создаём новый
    print("🔧 VLESS Inbound не найден, создаём новый...")
    
    # Генерируем ключи для Reality
    keygen_resp = session.get(f"{XUI_URL}panel/api/inbounds/generateRealityKey", timeout=10)
    if keygen_resp.status_code != 200:
        return None, "❌ Ошибка генерации ключей Reality"
    
    keys = keygen_resp.json().get("obj", {})
    public_key = keys.get("public_key", "")
    private_key = keys.get("private_key", "")
    
    # Настройки нового Inbound
    inbound_config = {
        "remark": "Auto-VLESS-Reality",
        "protocol": "vless",
        "port": 443,
        "settings": json.dumps({
            "clients": [],
            "decryption": "none"
        }),
        "streamSettings": json.dumps({
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "dest": "www.google.com:443",
                "xver": 0,
                "serverNames": ["www.google.com"],
                "privateKey": private_key,
                "publicKey": public_key,
                "shortIds": ["c9"],
                "settings": {"publicKey": public_key},
                "maxTimeDiff": 0,
                "clientSettings": {"publicKey": public_key},
                "fingerprint": "chrome"
            }
        }),
        "sniffing": json.dumps({
            "enabled": True,
            "destOverride": ["http", "tls"]
        })
    }
    
    # Отправляем запрос на создание
    create_resp = session.post(f"{XUI_URL}panel/api/inbounds/add", json=inbound_config, timeout=10)
    if create_resp.status_code == 200 and create_resp.json().get("success"):
        print("✅ VLESS Inbound успешно создан!")
        # Получаем ID нового Inbound
        new_resp = session.get(f"{XUI_URL}panel/api/inbounds/list", timeout=10)
        if new_resp.status_code == 200:
            for inbound in new_resp.json().get("obj", []):
                if inbound.get("protocol") == "vless":
                    return inbound.get("id"), None
        return None, "❌ Inbound создан, но не удалось получить его ID"
    else:
        return None, f"❌ Ошибка создания Inbound: {create_resp.text}"

# Получаем ID Inbound (один раз при запуске)
INBOUND_ID, ERROR_MSG = ensure_inbound_exists()
if ERROR_MSG:
    print(ERROR_MSG)
    INBOUND_ID = None

# ===== ФУНКЦИЯ СОЗДАНИЯ КЛЮЧА =====
def create_vpn_key(telegram_id, days):
    if not INBOUND_ID:
        return f"❌ {ERROR_MSG}"
    
    session = requests.Session()
    session.verify = False
    session.headers.update({"Content-Type": "application/json"})
    
    login_payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        login_resp = session.post(f"{XUI_URL}login", json=login_payload, timeout=10)
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            return "❌ Ошибка логина"
    except Exception as e:
        return f"❌ Ошибка: {e}"
    
    expiry_time = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
    email = f"user_{telegram_id}_{int(time.time())}"
    
    add_payload = {
        "id": INBOUND_ID,
        "settings": json.dumps({
            "clients": [{
                "id": "",
                "email": email,
                "expiryTime": expiry_time,
                "totalGB": 0,
                "enable": True
            }]
        })
    }
    
    try:
        add_resp = session.post(f"{XUI_URL}panel/api/inbounds/addClient", json=add_payload, timeout=10)
        if add_resp.status_code != 200:
            return f"❌ Ошибка HTTP: {add_resp.status_code}"
        add_json = add_resp.json()
        if not add_json.get("success"):
            return f"❌ Ошибка API: {add_json.get('msg')}"
        client_url = add_json.get("obj", {}).get("url")
        if client_url:
            return client_url
        return "❌ Ключ создан, но ссылка не получена"
    except Exception as e:
        return f"❌ Ошибка: {e}"

# ===== КЛАВИАТУРЫ =====
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
        InlineKeyboardButton("📱 1 месяц — 350 ₽", callback_data="buy_30"),
        InlineKeyboardButton("🎮 3 месяца — 900 ₽", callback_data="buy_90"),
        InlineKeyboardButton("⭐️ 6 месяцев — 1500 ₽", callback_data="buy_180"),
        InlineKeyboardButton("🔥 12 месяцев — 2500 ₽", callback_data="buy_365"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_main")
    )
    return keyboard

def back_button():
    return InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="back_main"))

# ===== ОБРАБОТЧИКИ =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔹 *VPN Shop* 🔹\n\n👇 Выберите действие:", parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    if call.data == "back_main":
        bot.edit_message_text("🔹 *VPN Shop* 🔹\n\n👇 Выберите действие:", chat_id, msg_id, parse_mode="Markdown", reply_markup=main_menu())
    elif call.data == "tariffs":
        bot.edit_message_text("📅 *Тарифы:*\n• 1 месяц — 350 ₽\n• 3 месяца — 900 ₽\n• 6 месяцев — 1500 ₽\n• 12 месяцев — 2500 ₽", chat_id, msg_id, parse_mode="Markdown", reply_markup=tariff_menu())
    elif call.data == "buy":
        bot.edit_message_text("📅 *Выберите срок:*", chat_id, msg_id, parse_mode="Markdown", reply_markup=tariff_menu())
    elif call.data == "support":
        bot.edit_message_text("🆘 *Поддержка*\n\n@твой_ник", chat_id, msg_id, parse_mode="Markdown", reply_markup=back_button())
    elif call.data == "channel":
        bot.edit_message_text("📢 *Канал:*\nhttps://t.me/твой_канал", chat_id, msg_id, reply_markup=back_button())
    elif call.data.startswith("buy_"):
        days = int(call.data.split("_")[1])
        user_id = call.from_user.id
        bot.edit_message_text(f"⏳ *Создаём ключ на {days} дней...*", chat_id, msg_id, parse_mode="Markdown")
        vpn_key = create_vpn_key(user_id, days)
        if vpn_key and vpn_key.startswith("vless://"):
            bot.edit_message_text(f"✅ *Ваш ключ:*\n`{vpn_key}`", chat_id, msg_id, parse_mode="Markdown", reply_markup=back_button())
        else:
            bot.edit_message_text(f"❌ {vpn_key}", chat_id, msg_id, parse_mode="Markdown", reply_markup=back_button())
    bot.answer_callback_query(call.id)

# ===== HTTP-СЕРВЕР ДЛЯ RENDER =====
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

print("✅ Бот запущен")
bot.infinity_polling()
