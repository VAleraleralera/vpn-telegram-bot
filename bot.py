import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- Главное меню (inline кнопки) ---
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(" Тарифы", callback_data="tariffs"),
        InlineKeyboardButton(" Купить", callback_data="buy"),
        InlineKeyboardButton(" Поддержка", callback_data="support"),
        InlineKeyboardButton(" Канал", callback_data="channel")
    )
    return keyboard

# --- Меню выбора тарифа ---
def tariff_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("1 месяц — 350 ₽", callback_data="tariff_1m"),
        InlineKeyboardButton("3 месяца — 900 ₽", callback_data="tariff_3m"),
        InlineKeyboardButton("6 месяцев — 1500 ₽", callback_data="tariff_6m"),
        InlineKeyboardButton("12 месяцев — 2500 ₽", callback_data="tariff_12m"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_main")
    )
    return keyboard

# --- Меню оплаты (после выбора тарифа) ---
def payment_menu(tariff, price):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить картой", callback_data=f"card_{tariff}_{price}"),
        InlineKeyboardButton("⭐ Telegram Stars", callback_data=f"stars_{tariff}_{price}"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_tariffs")
    )
    return keyboard

# --- Стартовая команда /start ---
@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "🔹 *VPN Shop* 🔹\n\n"
        "Работаем через обход блокировок.\n"
        "Ключи под Reality. Логи не храним.\n\n"
        "Оплата: карта, крипта, Telegram Stars.\n\n"
        "Выберите действие:"
    )
    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# --- Обработка всех нажатий на кнопки ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # Главное меню
    if call.data == "main_menu":
        bot.edit_message_text(
            "🔹 *VPN Shop* 🔹\n\nРаботаем через обход блокировок.\nКлючи под Reality. Логи не храним.\n\nВыберите действие:",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif call.data == "tariffs":
        bot.edit_message_text(
            "📅 *Выберите срок подписки:*",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=tariff_menu()
        )

    elif call.data == "buy":
        bot.edit_message_text(
            "📅 *Сначала выберите тариф:*",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=tariff_menu()
        )

    elif call.data == "support":
        text = (
            " *Поддержка*\n\n"
            "Если ключ не работает — перевыпустим в течение часа.\n"
            "Среднее время ответа: 15 минут.\n\n"
            "По вопросам: @твой_ник"
        )
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
        )

    elif call.data == "channel":
        text = " Наш канал: https://t.me/dnvzzz"
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
        )

    # Назад к тарифам
    elif call.data == "back_tariffs":
        bot.edit_message_text(
            " *Выберите срок подписки:*",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=tariff_menu()
        )

    elif call.data == "back_main":
        bot.edit_message_text(
            "🔹 *VPN Shop* 🔹\n\nРаботаем через обход блокировок.\nКлючи под Reality. Логи не храним.\n\nВыберите действие:",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    # --- Выбор тарифа ---
    elif call.data.startswith("tariff_"):
        tariff_map = {
            "tariff_1m": ("1 месяц", 350),
            "tariff_3m": ("3 месяца", 900),
            "tariff_6m": ("6 месяцев", 1500),
            "tariff_12m": ("12 месяцев", 2500)
        }
        tariff, price = tariff_map.get(call.data, ("Неизвестно", 0))
        bot.edit_message_text(
            f"✅ *Вы выбрали: {tariff} — {price} ₽*\n\nВыберите способ оплаты:",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=payment_menu(tariff, price)
        )

    # --- Оплата ---
    elif call.data.startswith("card_"):
        parts = call.data.split("_")
        tariff = parts[1]
        price = parts[2]
        text = (
            f"💳 *Оплата картой*\n\n"
            f"Тариф: {tariff} — {price} ₽\n\n"
            f"Реквизиты для перевода:\n"
            f"• Карта: 1234 5678 9012 3456\n"
            f"• Получатель: Иван Иванов\n\n"
            f"После оплаты пришлите чек сюда, и мы выдадим ключ в течение 5 минут."
        )
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ К тарифам", callback_data="back_tariffs"))
        )

    elif call.data.startswith("stars_"):
        parts = call.data.split("_")
        tariff = parts[1]
        price = parts[2]
        text = (
            f"⭐ *Оплата Telegram Stars*\n\n"
            f"Тариф: {tariff} — {price} ₽\n\n"
            f"Для оплаты перейдите по платёжной ссылке:\n"
            f"👉 [Оплатить Stars](https://t.me/здесь_твоя_ссылка)\n\n"
            f"После оплаты ключ придёт автоматически."
        )
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ К тарифам", callback_data="back_tariffs"))
        )

    # Обязательный ответ на callback (чтобы убрать часики)
    bot.answer_callback_query(call.id)

# --- HTTP-сервер для Render ---
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

print("✅ VPN Shop Bot (Inline) запущен")
bot.infinity_polling()
