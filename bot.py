import os
import telebot
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Создаём кнопки
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("💰 Цена"),
        KeyboardButton("🔑 Купить VPN"),
        KeyboardButton("❓ Помощь"),
        KeyboardButton("📢 Наш канал")
    )
    return keyboard

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "🤖 *Добро пожаловать в VPN Shop\\!*\n\n"
        "Мы продаём стабильные VPN ключи с хорошей скоростью.\n\n"
        "✅ *Никаких логов*\n"
        "✅ *Безлимит по трафику*\n"
        "✅ *Обход блокировок*\n\n"
        "👇 *Нажми на кнопку ниже*"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2", reply_markup=main_keyboard())

# Обработка ЛЮБОГО текста (включая кнопки)
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    text = message.text
    
    if "Цена" in text:
        answer = (
            "💎 *Тарифы:*\n\n"
            "📱 *1 месяц* — 150 руб\n"
            "🎮 *3 месяца* — 400 руб\n"
            "⭐️ *6 месяцев* — 700 руб\n"
            "🔥 *1 год* — 1200 руб\n\n"
            "💰 *Оплата:* карта, криптовалюта, Telegram Stars"
        )
        bot.send_message(message.chat.id, answer, parse_mode="MarkdownV2")
    
    elif "Купить" in text:
        vpn_key = "vless://example@example.com:443?security=reality"
        answer = (
            "🔑 *Ваш VPN ключ:*\n\n"
            f"`{vpn_key}`\n\n"
            "📱 *Как подключиться:*\n"
            "• Android: v2rayNG\n"
            "• Windows: v2rayN\n"
            "• iOS: Shadowrocket"
        )
        bot.send_message(message.chat.id, answer, parse_mode="MarkdownV2")
    
    elif "Помощь" in text or text == "/help":
        answer = (
            "🆘 *Помощь:*\n\n"
            "• `/start` — Главное меню\n"
            "• `/price` — Цены\n"
            "• `/buy` — Получить ключ\n\n"
            "⚡️ Если ключ не работает — напишите в поддержку"
        )
        bot.send_message(message.chat.id, answer, parse_mode="MarkdownV2")
    
    elif "Канал" in text:
        answer = "📢 Наш канал: https://t.me/твой_канал"
        bot.send_message(message.chat.id, answer)
    
    else:
        # Если ничего не подошло — показываем меню
        bot.send_message(message.chat.id, "Используй кнопки ниже 👇", reply_markup=main_keyboard())

# Команды /price, /buy, /help
@bot.message_handler(commands=['price'])
def price_cmd(message):
    handle_all(message)

@bot.message_handler(commands=['buy'])
def buy_cmd(message):
    handle_all(message)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    handle_all(message)

# HTTP-сервер для Render
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

print("✅ Бот запущен и работает...")
bot.infinity_polling()
