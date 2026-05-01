import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Импортируем нормальный клиент для 3X-UI
from client3x import Client3XUI, ClientPayload

# ----- ТВОИ НАСТРОЙКИ (ВСТАВЬ СВОИ ДАННЫЕ) -----
TOKEN = os.environ.get("BOT_TOKEN")
PANEL_URL = "http://72.56.119.147:54321/mKZdh18YN6yXlsRTkR/"  # Твой URL панели
PANEL_USERNAME = "admin"
PANEL_PASSWORD = "admin"
INBOUND_ID = 1  # ID твоего VLESS подключения (скорее всего 1)
# ------------------------------------------------

bot = telebot.TeleBot(TOKEN)

# --- ИНИЦИАЛИЗАЦИЯ API ---
# Это сердце автомата. Библиотека сама решит проблему с протоколом.
api_client = Client3XUI(
    panel_host=PANEL_URL,
    login=PANEL_USERNAME,
    password=PANEL_PASSWORD,
    inbound_id=INBOUND_ID,
    logging_enabled=True  # Чтобы видеть логи в Render
)

def create_vpn_key(user_telegram_id, days=30):
    """Создает ключ через API и возвращает VLESS-ссылку"""
    try:
        # 1. Создаем "клиента" (пользователя) для панели
        # Используем client3x для создания правильного JSON-запроса[citation:3]
        payload = ClientPayload(
            inbound_id=INBOUND_ID,
            user_id=user_telegram_id,
            email=f"user_{user_telegram_id}",
            expiry_days=days,  # библиотека сама переведет дни в timestamp
            traffic_GB=0,      # 0 = безлимит
            flow="xtls-rprx-vision"
        )
        
        # 2. Отправляем запрос в панель
        response = api_client.add_client(payload)
        
        if response.get('success'):
            # 3. Получаем ссылку на подключение
            # Ссылка обычно приходит в ответе или генерируется через get_client_url
            client_url = api_client.get_client_url(email=f"user_{user_telegram_id}")
            return client_url
        else:
            return None
    except Exception as e:
        print(f"🔥 Ошибка создания ключа: {e}")
        return None

# --- КЛАВИАТУРЫ ---
def tariff_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("1 месяц — 350 ₽", callback_data="buy_30"),
        InlineKeyboardButton("3 месяца — 900 ₽", callback_data="buy_90"),
        InlineKeyboardButton("6 месяцев — 1500 ₽", callback_data="buy_180")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "🔹 Добро пожаловать! Выбери тариф:", reply_markup=tariff_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    # Достаем количество дней из callback_data (buy_30 -> 30)
    days = int(call.data.split('_')[1])
    
    # Отправляем временное сообщение "Генерирую..."
    bot.edit_message_text("⏳ Создаю защищенный ключ...", call.message.chat.id, call.message.message_id)
    
    # --- МАГИЯ АВТОВЫДАЧИ ---
    # Вызываем нашу функцию. Она обратится к 3X-UI по API и создаст клиента.
    vless_link = create_vpn_key(call.from_user.id, days)
    
    if vless_link:
        answer_text = f"✅ *Ключ готов!*\n\n`{vless_link}`\n\nПодключение: Hiddify / v2rayNG / Nekoray"
        bot.edit_message_text(answer_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ Ошибка сервера. Напишите @admin", call.message.chat.id, call.message.message_id)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (ЧТОБ НЕ ЗАСЫПАЛ)---
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

# --- СТАРТ ---
print("✅ Супер-бот запущен. Автоматическая выдача активирована.")
bot.infinity_polling()
