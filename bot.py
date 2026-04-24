import os
import telebot

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Привет! Я бот для продажи VPN.\n\n💰 Цена: 150 руб/месяц\n📩 Для покупки напиши /buy")

@bot.message_handler(commands=['price'])
def price(message):
    bot.reply_to(message, "💰 Цена: 150 руб/месяц\n💳 Оплата: карта/крипта")

@bot.message_handler(commands=['buy'])
def buy(message):
    bot.reply_to(message, "🔑 Ключ: vless://example@example.com:443\n\n📱 Скачай v2rayNG (Android) / v2rayN (Windows)")

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Доступные команды:\n/start — приветствие\n/price — цена\n/buy — получить ключ\n/help — помощь")

print("✅ Бот запущен и работает...")
bot.infinity_polling()
