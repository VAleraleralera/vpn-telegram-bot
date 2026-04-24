import os
import telebot
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("💰 Цена"),
        KeyboardButton("🔑 Купить VPN"),
        KeyboardButton("❓ Помощь"),
        KeyboardButton("📢 Наш канал")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🤖 Добро пожаловать в VPN Shop!\n\nВыбери действие:",
        reply_markup=main_keyboard()
    )

# Обработка ТОЧНОГО совпадения текста кнопки
@bot.message_handler(func=lambda message: message.text == "💰 Цена")
def price(message):
    bot.send_message(
        message.chat.id,
        "💰 Тарифы:\n1 месяц — 150 руб\n3 месяца — 400 руб\n6 месяцев — 700 руб\n1 год — 1200 руб"
    )

@bot.message_handler(func=lambda message: message.text == "🔑 Купить VPN")
def buy(message):
    vpn_key = "vless://example@example.com:443?security=reality"
    bot.send_message(
        message.chat.id,
        f"🔑 Твой ключ:\n{vpn_key}\n\nСкачай v2rayNG (Android) или v2rayN (Windows)"
    )

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_command(message):
    bot.send_message(
        message.chat.id,
        "🆘 Помощь:\n/start — главное меню\n/price — цены\n/buy — получить ключ"
    )

@bot.message_handler(func=lambda message: message.text == "📢 Наш канал")
def channel(message):
    bot.send_message(message.chat.id, "Канал: https://t.me/твой_канал")

@bot.message_handler(commands=['price'])
def price_cmd(message):
    price(message)

@bot.message_handler(commands=['buy'])
def buy_cmd(message):
    buy(message)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_command(message)

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

print("✅ Бот запущен...")
bot.infinity_polling()
