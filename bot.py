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
        "👇 *Нажми на кнопку ниже, чтобы узнать цену*"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2", reply_markup=main_keyboard())

# Кнопка "💰 Цена"
@bot.message_handler(func=lambda message: message.text == "💰 Цена")
def price(message):
    text = (
        "💎 *Тарифы:*\n\n"
        "📱 *1 месяц* — 150 руб\n"
        "🎮 *3 месяца* — 400 руб\n"
        "⭐️ *6 месяцев* — 700 руб\n"
        "🔥 *1 год* — 1200 руб\n\n"
        "💰 *Оплата:* карта, криптовалюта, Telegram Stars\n\n"
        "🔑 Напиши /buy или нажми кнопку «Купить VPN»"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")

# Кнопка "🔑 Купить VPN"
@bot.message_handler(func=lambda message: message.text == "🔑 Купить VPN")
def buy(message):
    # ВРЕМЕННЫЙ КЛЮЧ — заменишь на настоящий позже
    vpn_key = "vless://example@example.com:443?security=reality"
    text = (
        "🔑 *Ваш VPN ключ:*\n\n"
        f"`{vpn_key}`\n\n"
        "📱 *Как подключиться:*\n"
        "• Android: скачать v2rayNG\n"
        "• Windows: скачать v2rayN\n"
        "• iOS: Shadowrocket (App Store)\n\n"
        "ℹ️ Если ключ не работает — напиши /help"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")

# Кнопка "❓ Помощь" и команда /help
@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
@bot.message_handler(commands=['help'])
def help_command(message):
    text = (
        "🆘 *Помощь:*\n\n"
        "• `/start` — Главное меню\n"
        "• `/price` — Цены\n"
        "• `/buy` — Получить ключ\n"
        "• `/help` — Это сообщение\n\n"
        "⚡️ Если ключ не работает — напишите в поддержку (ссылка появится позже)"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")

# Кнопка "📢 Наш канал"
@bot.message_handler(func=lambda message: message.text == "📢 Наш канал")
def channel(message):
    text = "📢 Подписывайся на наш канал: https://t.me/твой_канал"
    bot.send_message(message.chat.id, text)

# Команда /price
@bot.message_handler(commands=['price'])
def price_cmd(message):
    price(message)

# Команда /buy
@bot.message_handler(commands=['buy'])
def buy_cmd(message):
    buy(message)

# Простой HTTP-сервер для Render
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

# Запускаем HTTP-сервер в отдельном потоке
Thread(target=run_http_server, daemon=True).start()

# Запускаем бота
print("✅ Бот запущен и работает...")
bot.infinity_polling()
