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
    bot.send_message(message.chat.id, "🤖 Добро пожаловать!", reply_markup=main_keyboard())

# УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК (работает на телефоне и компе)
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    text = message.text
    
    if "Цена" in text or text == "💰 Цена":
        bot.send_message(message.chat.id, "💰 150 руб/месяц")
    
    elif "Купить" in text or text == "🔑 Купить VPN":
        bot.send_message(message.chat.id, "🔑 vless://example...")
    
    elif "Помощь" in text or text == "❓ Помощь":
        bot.send_message(message.chat.id, "🆘 /start - меню")
    
    elif "Канал" in text or text == "📢 Наш канал":
        bot.send_message(message.chat.id, "📢 https://t.me/твой_канал")
    
    else:
        bot.send_message(message.chat.id, "Используй кнопки 👇", reply_markup=main_keyboard())

# Обработка команд
@bot.message_handler(commands=['price', 'buy', 'help'])
def commands(message):
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

print("✅ Бот запущен")
bot.infinity_polling()
