import os
import telebot
import requests
import json
import time
from datetime import datetime, timedelta
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ (ЧЕРЕЗ ПЕРЕМЕННЫЕ RENDER) =====
TOKEN = os.environ.get("BOT_TOKEN")
XUI_URL = os.environ.get("XUI_URL")           # Твой URL панели (http://IP:порт/путь/)
XUI_USERNAME = os.environ.get("XUI_USERNAME") # Логин от панели (admin)
XUI_PASSWORD = os.environ.get("XUI_PASSWORD") # Пароль от панели (admin)

# Отключаем warnings про SSL (для красоты)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

bot = telebot.TeleBot(TOKEN)

# ===== 1. ПОЛУЧАЕМ ID НУЖНОГО INBOUND АВТОМАТИЧЕСКИ =====
def get_inbound_id():
    """Автоматически ищет ID первого попавшегося Inbound с протоколом VLESS."""
    session = requests.Session()
    session.verify = False
    session.headers.update({"Content-Type": "application/json"})
    
    # Логинимся в панели
    login_payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        login_resp = session.post(f"{XUI_URL}login", json=login_payload, timeout=10)
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            print("❌ Ошибка логина при поиске Inbound")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

    # Получаем список всех Inbound
    try:
        resp = session.get(f"{XUI_URL}panel/api/inbounds/list", timeout=10)
        if resp.status_code != 200:
            return None
        
        inbounds = resp.json().get("obj", [])
        
        # Ищем первый Inbound с протоколом VLESS
        for inbound in inbounds:
            if inbound.get("protocol") == "vless":
                inbound_id = inbound.get("id")
                print(f"✅ Найден Inbound ID {inbound_id} (протокол VLESS)")
                return inbound_id
        
        print("❌ Не найден ни один Inbound с протоколом VLESS")
        return None
    except Exception as e:
        print(f"Ошибка получения списка: {e}")
        return None

# Кэшируем ID, чтобы не дергать панель при каждом запросе (но панель не падает, так что можно и без кэша)
CACHED_INBOUND_ID = None

def get_cached_inbound_id():
    global CACHED_INBOUND_ID
    if CACHED_INBOUND_ID is None:
        CACHED_INBOUND_ID = get_inbound_id()
    return CACHED_INBOUND_ID

# ===== 2. СОЗДАНИЕ КЛЮЧА (РАБОТАЕТ С ЛЮБЫМ ID) =====
def create_vpn_key(telegram_id, days):
    """Создаёт клиента в 3X-UI и возвращает VLESS-ссылку"""
    inbound_id = get_cached_inbound_id()
    if not inbound_id:
        return None

    session = requests.Session()
    session.verify = False
    session.headers.update({"Content-Type": "application/json"})
    
    # Логинимся снова (или можно переиспользовать сессию, но для простоты — пусть логинится)
    login_payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        login_resp = session.post(f"{XUI_URL}login", json=login_payload, timeout=10)
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None
    
    # Подготавливаем данные клиента
    expiry_time = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
    email = f"user_{telegram_id}_{int(time.time())}"
    
    # Важно: структура запроса должна быть именно такой, как ждет 3X-UI
    add_payload = {
        "id": inbound_id,
        "settings": json.dumps({
            "clients": [{
                "id": "",  # Пустая строка — панель сама сгенерирует UUID
                "email": email,
                "expiryTime": expiry_time,
                "totalGB": 0,  # 0 = безлимит
                "enable": True
            }]
        })
    }
    
    try:
        add_resp = session.post(f"{XUI_URL}panel/api/inbounds/addClient", json=add_payload, timeout=10)
        if add_resp.status_code != 200:
            print(f"HTTP error: {add_resp.status_code}")
            return None
        
        add_json = add_resp.json()
        if not add_json.get("success"):
            print(f"API error: {add_json.get('msg')}")
            return None
        
        # Пытаемся получить ссылку из ответа
        client_url = add_json.get("obj", {}).get("url")
        if client_url:
            return client_url
        
        # Если ссылки нет — пробуем найти клиента в списке (подстраховка)
        inbounds_resp = session.get(f"{XUI_URL}panel/api/inbounds/get/{inbound_id}", timeout=10)
        if inbounds_resp.status_code == 200:
            clients = inbounds_resp.json().get("obj", {}).get("settings", {}).get("clients", [])
            for client in clients:
                if client.get("email") == email:
                    return client.get("url")
        
        return None
    except Exception as e:
        print(f"Add client error: {e}")
        return None

# ===== 3. КЛАВИАТУРЫ (БЕЗ ИЗМЕНЕНИЙ) =====
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

# ===== 4. ОБРАБОТЧИКИ =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🔹 *VPN Shop* 🔹\n\n🛡 Работаем через обход блокировок.\n📡 Ключи под Reality, логи не храним.\n\n👇 Выберите действие:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    if call.data == "back_main":
        bot.edit_message_text(
            "🔹 *VPN Shop* 🔹\n\nВыберите действие:",
            chat_id, msg_id, parse_mode="Markdown",
            reply_markup=main_menu()
        )
    
    elif call.data == "tariffs":
        bot.edit_message_text(
            "📅 *Наши тарифы:*\n\n• 1 месяц — 350 ₽\n• 3 месяца — 900 ₽\n• 6 месяцев — 1500 ₽\n• 12 месяцев — 2500 ₽\n\n💰 Оплата: карта, крипта, Stars\n\n👇 Выберите срок:",
            chat_id, msg_id, parse_mode="Markdown",
            reply_markup=tariff_menu()
        )
    
    elif call.data == "buy":
        bot.edit_message_text(
            "📅 *Выберите срок подписки:*",
            chat_id, msg_id, parse_mode="Markdown",
            reply_markup=tariff_menu()
        )
    
    elif call.data == "support":
        text = "🆘 *Поддержка*\n\nПо вопросам: @твой_ник\n\n⚡️ Если ключ не работает — перевыпустим в течение часа."
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=back_button())
    
    elif call.data == "channel":
        text = "📢 *Наш канал:*\nhttps://t.me/твой_канал"
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=back_button())
    
    elif call.data.startswith("buy_"):
        days = int(call.data.split("_")[1])
        user_id = call.from_user.id
        
        bot.edit_message_text(
            f"⏳ *Создаём ключ на {days} дней...*\n\nЭто может занять до 10 секунд.",
            chat_id, msg_id, parse_mode="Markdown"
        )
        
        vpn_key = create_vpn_key(user_id, days)
        
        if vpn_key and vpn_key.startswith("vless://"):
            text = (
                f"✅ *Оплата получена!*\n\n"
                f"📅 *Срок:* {days} дней\n\n"
                f"🔑 *Ваш ключ:*\n`{vpn_key}`\n\n"
                f"📱 *Как подключиться:*\n"
                f"• Android: v2rayNG / Hiddify\n"
                f"• Windows: v2rayN / Hiddify\n"
                f"• iOS: Shadowrocket / Hiddify\n\n"
                f"💾 *Сохраните ключ!* Он действителен {days} дней."
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=back_button())
        else:
            bot.edit_message_text(
                f"❌ *Ошибка создания ключа*\n\n"
                f"Пожалуйста, напишите администратору: @твой_ник\n"
                f"Сообщите это: {vpn_key if vpn_key else 'API не ответил'}",
                chat_id, msg_id, parse_mode="Markdown",
                reply_markup=back_button()
            )
    
    bot.answer_callback_query(call.id)

# ===== 5. HTTP-СЕРВЕР ДЛЯ RENDER =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')
    
    def log_message(self, format, *args):
        pass  # заглушаем лишние логи

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

Thread(target=run_http_server, daemon=True).start()

# ===== 6. ЗАПУСК =====
print("✅ Бот запущен. Автоматический поиск Inbound и выдача ключей активна.")
bot.infinity_polling()
