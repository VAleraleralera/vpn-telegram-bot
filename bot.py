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

# Отключаем предупреждения о SSL (для диагностики)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_vpn_key(expiry_days):
    try:
        print(f"🔍 Начинаем диагностику...")
        print(f"URL: {XUI_URL}")
        print(f"Username: {XUI_USERNAME}")
        
        session = requests.Session()
        session.verify = False
        
        # Шаг 1: Логин
        print("1️⃣ Пытаемся залогиниться...")
        login_resp = session.post(f"{XUI_URL}login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD}, timeout=10)
        print(f"Статус логина: {login_resp.status_code}")
        print(f"Ответ: {login_resp.text[:200] if login_resp.text else 'пусто'}")
        
        if login_resp.status_code != 200:
            return f"Ошибка: панель не ответила (код {login_resp.status_code})"
        
        login_json = login_resp.json()
        if not login_json.get("success"):
            return f"Ошибка логина: {login_json.get('msg', 'неизвестная ошибка')}"
        
        print("✅ Логин успешен!")
        
        # Шаг 2: Получаем список inbound
        print("2️⃣ Получаем список подключений...")
        inbounds_resp = session.get(f"{XUI_URL}panel/api/inbounds/list", timeout=10)
        print(f"Статус: {inbounds_resp.status_code}")
        
        if inbounds_resp.status_code != 200:
            return f"Ошибка получения списка: код {inbounds_resp.status_code}"
        
        data = inbounds_resp.json()
        inbounds = data.get("obj", [])
        print(f"Найдено inbound: {len(inbounds)}")
        
        # Ищем vless inbound
        inbound_id = None
        for inbound in inbounds:
            print(f"  - ID: {inbound.get('id')}, Протокол: {inbound.get('protocol')}")
            if inbound.get("protocol") == "vless":
                inbound_id = inbound.get("id")
                break
        
        if not inbound_id:
            return "Ошибка: не найден VLESS inbound. Создайте его в панели 3X-UI"
        
        print(f"✅ Найден inbound ID: {inbound_id}")
        
        # Шаг 3: Создаём клиента
        print("3️⃣ Создаём клиента...")
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
        
        add_resp = session.post(f"{XUI_URL}panel/api/inbounds/addClient", json=payload, timeout=10)
        print(f"Статус создания: {add_resp.status_code}")
        print(f"Ответ: {add_resp.text[:300] if add_resp.text else 'пусто'}")
        
        if add_resp.status_code == 200:
            result = add_resp.json()
            if result.get("success"):
                client_url = result.get("obj", {}).get("url")
                if client_url:
                    return client_url
                else:
                    return f"Клиент создан, но не получена ссылка. Ответ: {result}"
            else:
                return f"Ошибка API: {result.get('msg', 'неизвестная ошибка')}"
        else:
            return f"HTTP ошибка {add_resp.status_code}: {add_resp.text[:200]}"
            
    except requests.exceptions.ConnectionError as e:
        return f"Ошибка подключения к панели: {e}"
    except Exception as e:
        return f"Общая ошибка: {type(e).__name__}: {e}"

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
        InlineKeyboardButton("1 месяц — 350 ₽", callback_data="tariff_1m"),
        InlineKeyboardButton("3 месяца — 900 ₽", callback_data="tariff_3m"),
        InlineKeyboardButton("6 месяцев — 1500 ₽", callback_data="tariff_6m"),
        InlineKeyboardButton("12 месяцев — 2500 ₽", callback_data="tariff_12m"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_main")
    )
    return keyboard

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
        bot.edit_message_text(f"🔍 *Результат диагностики:*\n`{key}`", chat_id, msg_id, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="back_main")))
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

print("✅ Диагностический бот запущен")
bot.infinity_polling()
