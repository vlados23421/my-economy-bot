import os
import logging
from typing import Dict, Optional

import telebot
from telebot import types
from flask import Flask, request, abort

# ─────────────────────────── ПЕРЕМЕННЫЕ ───────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "") or "8992162127:AAH-FF5MtWhahVBeNufUn7KXnQllb9MS-tA"
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WEBHOOK_URL = os.environ.get("https://my-economy-bot.onrender.com", "")

SERVER_IP = "188.127.241.74:3635"
SERVER_NAME = "BEST RUSSIA"
DISCORD_LINK = "https://discord.gg/qqHqy3mGg"

# ─────────────────────────── ЛОГГЕР ───────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────── БОТ ───────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_states: Dict[int, Optional[str]] = {}

# ─────────────────────────── КЛАВИАТУРЫ ───────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 Правила", "🌐 IP сервера")
    markup.add("📝 Подать жалобу", "🆘 Помощь / FAQ")
    markup.add("📞 Связаться с администрацией")
    return markup

def remove_kb():
    return types.ReplyKeyboardRemove()

def rules_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Общие правила", callback_data="rules_common"),
        types.InlineKeyboardButton("Правила RP", callback_data="rules_rp"),
        types.InlineKeyboardButton("Правила чата", callback_data="rules_chat"),
        types.InlineKeyboardButton("Система наказаний", callback_data="rules_punish"),
    )
    return markup

def faq_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Как зайти на сервер?", callback_data="faq_join"),
        types.InlineKeyboardButton("Не заходит в игру / ошибка", callback_data="faq_crash"),
        types.InlineKeyboardButton("Как получить разбан?", callback_data="faq_unban"),
        types.InlineKeyboardButton("Где скачать лаунчер?", callback_data="faq_mods"),
        types.InlineKeyboardButton("Потерял прогресс / вещи", callback_data="faq_progress"),
    )
    return markup

# ─────────────────────────── ТЕКСТЫ ───────────────────────────
RULES = {
    "common": (
        "📜 <b>Общие правила сервера BEST RUSSIA</b>\n\n"
        "1. Запрещены читы, трейнеры и любые сторонние программы.\n"
        "2. Уважайте других игроков.\n"
        "3. Запрещена реклама других проектов.\n"
        "4. Запрещено использование багов игры.\n"
        "5. Администратор всегда прав."
    ),
    "rp": (
        "📜 <b>Правила RP (RolePlay)</b>\n\n"
        "1. Не выходите из роли (NonRP).\n"
        "2. Запрещён PowerGaming (PG).\n"
        "3. Запрещён Metagaming (MG).\n"
        "4. Соблюдайте реалистичность действий."
    ),
    "chat": (
        "📜 <b>Правила общения в чатах</b>\n\n"
        "1. Запрещён спам и флуд.\n"
        "2. Оскорбления и токсичное поведение наказываются.\n"
        "3. Запрещено злоупотребление Caps Lock.\n"
        "4. Реклама сторонних ресурсов — бан."
    ),
    "punish": (
        "📜 <b>Система наказаний</b>\n\n"
        "1. Предупреждение / Кик\n"
        "2. Мут на 30 минут\n"
        "3. Бан на 1 день\n"
        "4. Перманентный бан"
    ),
}

FAQ = {
    "join": f"🌐 Чтобы зайти на сервер, запустите наш лаунчер, <code>{SERVER_IP}</code> в избранное и подключитесь.",
    "crash": (
        "🔧 <b>Не заходит в игру / ошибка</b>\n\n"
        "- Установите лаунчер.\n"
        "- Введите свой никнейм.\n"
        "- Проверьте антивирус.\n"
        "- Если проблема осталась — обратитесь в техподдержку."
    ),
    "unban": f"🔓 <b>Как получить разбан?</b>\n\nЗаявки на разбан подаются через Discord: {DISCORD_LINK}",
    "mods": f"📦 <b>Где скачать лаунчер?</b>\n\nАктуальная лаунчер в Discord: {DISCORD_LINK}",
    "progress": (
        "💾 <b>Потерял прогресс / вещи</b>\n\n"
        "Напишите в поддержку, указав никнейм и примерную дату. Мы проверим логи."
    ),
}

# ─────────────────────────── ОБРАБОТЧИКИ ───────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id,
        f"⚡️ Добро пожаловать в бот поддержки сервера <b>{SERVER_NAME}</b>!\n"
        "Чем я могу помочь? Выберите раздел ниже:",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "📋 Правила")
def rules_menu(message):
    bot.send_message(message.chat.id, "📋 Выберите раздел правил:", reply_markup=rules_keyboard())

@bot.message_handler(func=lambda m: m.text == "🌐 IP сервера")
def ip_info(message):
    bot.send_message(
        message.chat.id,
        f"🌍 <b>IP адрес сервера:</b> <code>{SERVER_IP}</code>\n\n"
        "Для подключения используйте лаунчер."
    )

@bot.message_handler(func=lambda m: m.text == "📝 Подать жалобу")
def complaint_start(message):
    user_states[message.chat.id] = 'complaint'
    bot.send_message(
        message.chat.id,
        "📝 <b>Подача жалобы на игрока</b>\n\n"
        "Опишите ситуацию: ник нарушителя, что произошло, когда, приложите доказательства.\n"
        "Отправьте всё одним сообщением.\n"
        "Для отмены нажмите /start.",
        reply_markup=remove_kb()
    )

@bot.message_handler(func=lambda m: m.text == "🆘 Помощь / FAQ")
def help_menu(message):
    bot.send_message(message.chat.id, "🆘 Часто задаваемые вопросы:", reply_markup=faq_keyboard())

@bot.message_handler(func=lambda m: m.text == "📞 Связаться с администрацией")
def contact(message):
    user_states[message.chat.id] = 'contact'
    bot.send_message(
        message.chat.id,
        "📞 Вы перешли в режим связи с администрацией.\n"
        "Напишите ваш вопрос, и мы ответим в ближайшее время.\n"
        "Для выхода нажмите /start.",
        reply_markup=remove_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'complaint')
def process_complaint(message):
    user_states[message.chat.id] = None
    complaint_id = f"ЖАЛОБА-{message.date.strftime('%Y%m%d%H%M%S')}"
    admin_text = (
        f"📨 <b>Новая жалоба</b>\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: <code>{message.chat.id}</code>\n"
        f"Номер: <b>{complaint_id}</b>\n\n"
        f"{message.text}"
    )
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, admin_text)
    bot.send_message(
        message.chat.id,
        f"✅ Ваша жалоба принята (№ {complaint_id}). Администрация рассмотрит её в ближайшее время.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'contact')
def forward_contact(message):
    admin_text = (
        f"📩 <b>Сообщение от пользователя</b>\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: <code>{message.chat.id}</code>\n\n"
        f"{message.text}"
    )
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, admin_text)
    bot.send_message(message.chat.id, "✅ Ваше сообщение отправлено администрации. Ожидайте ответа.")

@bot.message_handler(commands=['reply'])
def admin_reply(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Использование: /reply <user_id> <текст>")
        return
    user_id, reply_text = parts[1], parts[2]
    try:
        bot.send_message(int(user_id), f"💬 <b>Ответ от администрации {SERVER_NAME}:</b>\n{reply_text}")
        bot.send_message(message.chat.id, f"✅ Ответ отправлен пользователю {user_id}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при отправке: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rules_"))
def rules_callback(call):
    key = call.data.replace("rules_", "")
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, RULES.get(key, "Раздел не найден."))

@bot.callback_query_handler(func=lambda call: call.data.startswith("faq_"))
def faq_callback(call):
    key = call.data.replace("faq_", "")
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, FAQ.get(key, "Ответ не найден."))

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(message.chat.id, "Используйте кнопки меню или нажмите /start для возврата в главное меню.")

# ─────────────────────────── FLASK ───────────────────────────
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@app.route('/')
def index():
    return f"{SERVER_NAME} support bot is running."

# ─────────────────────────── ЗАПУСК ───────────────────────────
if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
        logger.info(f"Webhook установлен: {WEBHOOK_URL}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        bot.remove_webhook()
        logger.info("Запуск в режиме polling...")
        bot.infinity_polling()
