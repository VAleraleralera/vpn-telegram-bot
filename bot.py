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

# ========== ТВОИ ДАННЫЕ ==========
TOKEN = "8703864624:AAGzkhvrv93U6k0a-6FNMz_ieeL8SQXQiVk"
XUI_URL = "http://72.56.119.147:8443/L7nSikoltRgG5CM2GC"
XUI_USERNAME = "VPn/Admin.log"
XUI_PASSWORD = "Vpn/AdMin.pas"

bot = telebot.TeleBot(TOKEN)

def create_vpn_key(days):
    session = requests.Session()
    
    # 1. Логинимся и получаем куки
    try:
        login_resp = session.post(f"{XUI_URL}/login", json={"username": XUI_USERNAME, "password": XUI_PASSWORD}, timeout=10)
        if login_resp.status_code != 200 or not login_resp.json().get("success"):
            return "❌ Ошибка авторизации в панели"
    except Exception as e:
        return f"❌ Ошибка подключения: {e}"
    
    # 2. Получаем список Inbound и находим VLESS
    try:
        inbounds_resp = session.get(f"{XUI_URL}/panel/api/inbounds/list", timeout=10)
        if inbounds_resp.status_code != 200:
            return f"❌ Ошибка получения списка: {inbounds_resp.status_code}"
        
        inbounds = inbounds_resp.json().get("obj", [])
        inbound_id = None
        inbound_port = None
        for inbound in inbounds:
            if inbound.get("protocol") == "vless":
                inbound_id = inbound.get("id")
                inbound_port = inbound.get("port")
                break
        
        if not inbound_id:
            return "❌ VLESS Inbound не найден. Создайте его в панели (порт 8443, протокол VLESS)"
    except Exception as e:
        return f"❌ Ошибка получения Inbound: {e}"
    
    # 3. Создаём клиента
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
    
    try:
        add_resp = session.post(f"{XUI_URL}/panel/api/inbounds/addClient", json=payload, timeout=30)
        if add_resp.status_code != 200:
            return f"❌ HTTP ошибка: {add_resp.status_code}"
        
        result = add_resp.json()
        if not result.get("success"):
            return f"❌ Ошибка API: {result.get('msg')}"
        
        # Пробуем получить URL из ответа
        client_url = result.get("obj", {}).get("url")
        if client_url:
            # Убеждаемся, что порт правильный
            if f":{inbound_port}" not in client_url.split("?")[0]:
                # Если порт в URL не совпадает с реальным — подменяем
                client_url = client_url.replace(":443", f":{inbound_port}")
            return client_url
        
        # Если URL нет — собираем вручную (но такого быть не должно)
        host = XUI_URL.split("//")[1].split("/")[0].split(":")[0]
        return f"vless://{client_id}@{host}:{inbound_port}?flow=xtls-rprx-vision&encryption=none&security=reality&sni=www.google.com&fp=chrome&pbk=GEZbGybRfgK1eKGyZqBdnZEoVmsqQ0o6LSEItu6WQVE&type=tcp&headerType=none#{email}"
    
    except Exception as e:
        return f"❌ Ошибка создания: {e}"

# ========== КЛАВИАТУРЫ ==========
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

print("✅ Бот запущен. Автовыдача ключей активна.")
bot.infinity_polling()
