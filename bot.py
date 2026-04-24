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
        KeyboardButton(" Тарифы"),
        KeyboardButton(" Купить"),
        KeyboardButton(" Поддержка"),
        KeyboardButton(" Канал")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "VPN Shop. Работаем через обход блокировок.\n\n"
        "Ключи под Reality. Логи не храним. Оплата — карта, крипта, Stars.\n\n"
        "Выберите действие в меню ниже."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: "Тариф" in message.text or message.text == "💰 Тарифы")
def price(message):
    text = (
        "Тарифы:\n\n"
        "1 месяц — 350 ₽\n"
        "3 месяца — 900 ₽\n"
        "6 месяцев — 1500 ₽\n"
        "12 месяцев — 2500 ₽\n\n"
        "Оплата любым способом. Выдаём ключ в течение 5 минут.\n\n"
        "Чтобы купить — нажмите «Купить»."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: "Купить" in message.text or message.text == "🔑 Купить")
def buy(message):
    text = (
        "Сейчас подключение выдаётся вручную.\n\n"
        "Оплату отправляйте сюда:\n"
        "👉 89091110340 сбер бля\n\n"
        "После оплаты скиньте чек сюда — получите ключ.\n\n"
        "Подключение: V2Ray / Nekoray / Hiddify."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: "Поддерж" in message.text or message.text == "❓ Поддержка")
def support(message):
    text = (
        "Если ключ не работает — перевыпустим в течение часа.\n\n"
        "Среднее время ответа: 15 минут (днём).\n\n"
        "По техническим вопросам сюда:\n"
        "👉 @@dnvzzz"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: "Канал" in message.text or message.text == "📢 Канал")
def channel(message):
    text = "📢 Наш канал: https://t.me/нету пока канала"
    bot.send_message(message.chat.id, text)

# Обработка команд
@bot.message_handler(commands=['price'])
def price_cmd(message):
    price(message)

@bot.message_handler(commands=['buy'])
def buy_cmd(message):
    buy(message)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    support(message)

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

print("✅ VPN Shop Bot запущен")
bot.infinity_polling()
