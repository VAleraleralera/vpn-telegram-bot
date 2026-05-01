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
XUI_URL = os.environ.get("XUI_URL")           # http://72.56.119.147:54321/твой_путь/
XUI_USERNAME = os.environ.get("XUI_USERNAME") # логин от панели (admin)
XUI_PASSWORD = os.environ.get("XUI_PASSWORD") # пароль от панели

# Отключаем warnings про SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

bot = telebot.TeleBot(TOKEN)

# ===== 1. ПОЛУЧАЕМ ID НУЖНОГО INBOUND АВТОМАТИЧЕСКИ =====
def get_inbound_id():
    """Автоматически ищет ID первого попавшегося Inbound с протоколом VLESS."""
    session = requests.Session()
    session.verify = False
    session.headers.update({"Content-Type": "application/json"})
    
    print(f"[DIAG] Пытаюсь залогиниться в {XUI_URL}login")
    
    # Логинимся в панели
    login_payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        login_resp = session.post(f"{XUI_URL}login", json=login_payload, timeout=10)
        print(f"[DIAG] Логин ответ: {login_resp.status_code}")
        if login_resp.status_code != 200:
            print(f"[DIAG] Тело ответа: {login_resp.text[:200]}")
            return None
        login_json = login_resp.json()
        if not login_json.get("success"):
            print(f"[DIAG] Ошибка логина API: {login_json.get('msg')}")
            return None
    except Exception as e:
        print(f"[DIAG] Ошибка логина: {e}")
        return None
    
    print("[DIAG] Логин успешен, получаем список Inbound...")
    
    # Получаем список всех Inbound
    try:
        resp = session.get(f"{XUI_URL}panel/api/inbounds/list", timeout=10)
        print(f"[DIAG] Список Inbound ответ: {resp.status_code}")
        if resp.status_code != 200:
            print(f"[DIAG] Тело ответа: {resp.text[:200]}")
            return None
        
        data = resp.json()
        inbounds = data.get("obj", [])
        print(f"[DIAG] Найдено Inbound: {len(inbounds)}")
        
        # Ищем первый Inbound с протоколом VLESS
        for inbound in inbounds:
            protocol = inbound.get("protocol")
            inbound_id = inbound.get("id")
            remark = inbound.get("remark", "без имени")
            print(f"[DIAG] Inbound ID {inbound_id}: {protocol} ({remark})")
            if protocol == "vless":
                print(f"[DIAG] ✅ ВЫБРАН Inbound ID {inbound_id}")
                return inbound_id
        
        print("[DIAG] ❌ Не найден Inbound с протоколом VLESS")
        return None
    except Exception as e:
        print(f"[DIAG] Ошибка получения списка: {e}")
        return None

# Кэшируем ID
CACHED_INBOUND_ID = None

def get_cached_inbound_id():
    global CACHED_INBOUND_ID
    if CACHED_INBOUND_ID is None:
        CACHED_INBOUND_ID = get_inbound_id()
    return CACHED_INBOUND_ID

# ===== 2. СОЗДАНИЕ КЛЮЧА С ДИАГНОСТИКОЙ =====
def create_vpn_key(telegram_id, days):
    """Создаёт клиента в 3X-UI и возвращает VLESS-ссылку или текст ошибки"""
    result = []
    
    inbound_id = get_cached_inbound_id()
    if not inbound_id:
        return "❌ Ошибка: не найден VLESS Inbound. Создайте его в панели 3X-UI"
    
    result.append(f"🔍 Найден Inbound ID: {inbound_id}")
    
    session = requests.Session()
    session.verify = False
    session.headers.update({"Content-Type": "application/json"})
    
    # Логинимся
    login_payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        login_resp = session.post(f"{XUI_URL}login", json=login_payload, timeout=10)
        result.append(f"🔐 Логин: HTTP {login_resp.status_code}")
        if login_resp.status_code != 200:
            return "\n".join(result) + f"\n\n❌ Ошибка логина: HTTP {login_resp.status_code}"
        login_json = login_resp.json()
        if not login_json.get("success"):
            return "\n".join(result) + f"\n\n❌ Ошибка логина: {login_json.get('msg')}"
    except Exception as e:
        return "\n".join(result) + f"\n\n❌ Ошибка соединения: {type(e).__name__} {e}"
    
    result.append("✅ Авторизация успешна")
    
    # Создаём клиента
    expiry_time = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
    email = f"user_{telegram_id}_{int(time.time())}"
    
    add_payload = {
        "id": inbound_id,
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
        result.append(f"📤 Создание клиента: HTTP {add_resp.status_code}")
        
        if add_resp.status_code != 200:
            return "\n".join(result) + f"\n\n❌ Ошибка HTTP: {add_resp.status_code}"
        
        add_json = add_resp.json()
        if not add_json.get("success"):
            return "\n".join(result) + f"\n\n❌ Ошибка API: {add_json.get('msg', 'неизвестная')}"
        
        client_url = add_json.get("obj", {}).get("url")
        if client_url:
            result.append("✅ Ключ получен!")
            return client_url
        else:
            return "\n".join(result) + f"\n\n❌ Ключ создан, но ссылка не найдена.\nОтвет: {add_json}"
            
    except Exception as e:
        return "\n".join(result) + f"\n\n❌ Ошибка запроса: {type(e).__name__} {e}"

# ===== 3. КЛАВИАТУРЫ =====
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
                f"❌ *Ошибка создания ключа*\n\n```\n{vpn_key}\n```\n\nПожалуйста, напишите администратору.",
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
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

Thread(target=run_http_server, daemon=True).start()

# ===== 6. ЗАПУСК =====
print("✅ Бот запущен. Диагностика включена.")
bot.infinity_polling()
