import os
import logging
import datetime
from typing import Dict, Optional

import telebot
from telebot import types
from flask import Flask, request, abort

# ─────────────────────────── ПЕРЕМЕННЫЕ ───────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

SERVER_IP = "188.127.241.74:3635"
SERVER_NAME = "BEST RUSSIA"
DISCORD_LINK = "https://discord.gg/qqHqy3mGg"
VK_LINK = "https://vk.ru/bestrussiaonlinerp"
DONATE_LINK = "t.me/HowManyVaj"

# ─────────────────────────── ЛОГГЕР ───────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────── БОТ ───────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_states: Dict[int, Optional[str]] = {}

# Хранилище тикетов
tickets: Dict[str, dict] = {}
ticket_counter = 0

# Новости сервера (можно менять через админку)
server_news = "⚡️ Новый сезон! Заходите и играйте с друзьями!"

# ─────────────────────────── КЛАВИАТУРЫ ───────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 Правила", "🌐 IP сервера")
    markup.add("📝 Подать жалобу", "🔓 Заявка на разбан")
    markup.add("🆘 Помощь / FAQ", "📞 Связь с админом")
    markup.add("💰 Донат", "👥 Онлайн сервера")
    markup.add("📰 Новости", "❓ Для новичков")
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
        types.InlineKeyboardButton("Где скачать сборку?", callback_data="faq_mods"),
        types.InlineKeyboardButton("Потерял прогресс / вещи", callback_data="faq_progress"),
    )
    return markup

def donate_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💎 Купить донат", url=DONATE_LINK),
        types.InlineKeyboardButton("📋 Список привилегий", callback_data="donate_list"),
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
        "5. Администратор всегда прав.\n\n"
        "За нарушение — бан от 1 дня до перманентного."
    ),
    "rp": (
        "📜 <b>Правила RP (RolePlay)</b>\n\n"
        "1. Не выходите из роли (NonRP) — запрещено обсуждать реальный мир в IC чате.\n"
        "2. Запрещён PowerGaming (PG) — навязывание действий без шанса на ответ.\n"
        "3. Запрещён Metagaming (MG) — использование OOC информации в IC.\n"
        "4. Запрещён Deathmatching (DM) — убийство без RP причины.\n"
        "5. Запрещён Revenge Kill (RK) — месть после смерти.\n"
        "6. Соблюдайте реалистичность действий."
    ),
    "chat": (
        "📜 <b>Правила общения в чатах</b>\n\n"
        "1. Запрещён спам и флуд.\n"
        "2. Оскорбления и токсичное поведение — мут/бан.\n"
        "3. Запрещено злоупотребление Caps Lock.\n"
        "4. Реклама сторонних ресурсов — перманентный бан.\n"
        "5. Уважайте собеседников."
    ),
    "punish": (
        "📜 <b>Система наказаний</b>\n\n"
        "1. Предупреждение / Кик\n"
        "2. Мут на 30 минут / 1 час / 1 день\n"
        "3. Бан на 1 день / 3 дня / 7 дней\n"
        "4. Перманентный бан\n\n"
        "Наказание зависит от тяжести нарушения и истории игрока."
    ),
}

FAQ = {
    "join": f"🌐 Чтобы зайти на сервер, запустите SA-MP, добавьте IP <code>{SERVER_IP}</code> в избранное и подключитесь.",
    "crash": (
        "🔧 <b>Не заходит в игру / ошибка</b>\n\n"
        "- Установите SA-MP 0.3.7-R1.\n"
        "- Скачайте нашу сборку модов.\n"
        "- Проверьте антивирус.\n"
        "- Запустите от имени администратора.\n"
        "- Если проблема осталась — обратитесь в техподдержку."
    ),
    "unban": f"🔓 <b>Как получить разбан?</b>\n\nЗаявки на разбан подаются через Discord: {DISCORD_LINK}\nИли используйте кнопку «Заявка на разбан» в боте.",
    "mods": f"📦 <b>Где скачать сборку?</b>\n\nАктуальная сборка в Discord: {DISCORD_LINK}\nТам же найдёте инструкцию по установке.",
    "progress": (
        "💾 <b>Потерял прогресс / вещи</b>\n\n"
        "Напишите в поддержку через кнопку «Связь с админом», указав:\n"
        "- Ваш никнейм\n"
        "- Примерную дату потери\n"
        "- Что именно потеряно\n"
        "Мы проверим логи и поможем."
    ),
}

# ─────────────────────────── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ───────────────────────────
def create_ticket(user_id: int, ticket_type: str, text: str) -> str:
    global ticket_counter
    ticket_counter += 1
    ticket_id = f"#{ticket_counter:04d}"
    tickets[ticket_id] = {
        "user_id": user_id,
        "type": ticket_type,
        "text": text,
        "status": "open",
        "created": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    return ticket_id

# ─────────────────────────── ОБРАБОТЧИКИ ───────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id,
        f"⚡️ Добро пожаловать в бот поддержки сервера <b>{SERVER_NAME}</b>!\n\n"
        f"📰 <b>Новости:</b> {server_news}\n\n"
        "Чем я могу помочь? Выберите раздел ниже:",
        reply_markup=main_keyboard()
    )

# ── Правила ──
@bot.message_handler(func=lambda m: m.text == "📋 Правила")
def rules_menu(message):
    bot.send_message(message.chat.id, "📋 Выберите раздел правил:", reply_markup=rules_keyboard())

# ── IP сервера ──
@bot.message_handler(func=lambda m: m.text == "🌐 IP сервера")
def ip_info(message):
    bot.send_message(
        message.chat.id,
        f"🌍 <b>IP адрес сервера:</b> <code>{SERVER_IP}</code>\n\n"
        "Для подключения используйте SA-MP 0.3.7-R1.\n"
        f"Сборка модов и инструкция в Discord: {DISCORD_LINK}"
    )

# ── Жалоба ──
@bot.message_handler(func=lambda m: m.text == "📝 Подать жалобу")
def complaint_start(message):
    user_states[message.chat.id] = 'complaint'
    bot.send_message(
        message.chat.id,
        "📝 <b>Подача жалобы на игрока</b>\n\n"
        "Опишите ситуацию в одном сообщении:\n"
        "- Никнейм нарушителя\n"
        "- Что произошло\n"
        "- Когда (примерное время)\n"
        "- Доказательства (можно прикрепить фото/видео)\n\n"
        "Для отмены нажмите /start.",
        reply_markup=remove_kb()
    )

@bot.message_handler(content_types=['photo', 'video', 'document'], func=lambda m: user_states.get(m.chat.id) == 'complaint')
def complaint_media(message):
    """Обработка фото/видео в жалобе."""
    user_states[message.chat.id] = None
    ticket_id = create_ticket(message.chat.id, "Жалоба", "Медиа-файл прилагается")
    
    caption = message.caption or "Без описания"
    admin_text = (
        f"📨 <b>Новая жалоба</b>\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: <code>{message.chat.id}</code>\n"
        f"Тикет: <b>{ticket_id}</b>\n\n"
        f"Описание: {caption}"
    )
    
    if ADMIN_CHAT_ID:
        # Пересылаем медиа
        if message.photo:
            bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=admin_text)
        elif message.video:
            bot.send_video(ADMIN_CHAT_ID, message.video.file_id, caption=admin_text)
        elif message.document:
            bot.send_document(ADMIN_CHAT_ID, message.document.file_id, caption=admin_text)
    
    bot.send_message(
        message.chat.id,
        f"✅ Ваша жалоба принята (тикет {ticket_id}). Администрация рассмотрит её в ближайшее время.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'complaint')
def process_complaint(message):
    user_states[message.chat.id] = None
    ticket_id = create_ticket(message.chat.id, "Жалоба", message.text)
    
    admin_text = (
        f"📨 <b>Новая жалоба</b>\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: <code>{message.chat.id}</code>\n"
        f"Тикет: <b>{ticket_id}</b>\n\n"
        f"{message.text}"
    )
    
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, admin_text)
    
    bot.send_message(
        message.chat.id,
        f"✅ Ваша жалоба принята (тикет {ticket_id}). Администрация рассмотрит её в ближайшее время.",
        reply_markup=main_keyboard()
    )

# ── Заявка на разбан ──
@bot.message_handler(func=lambda m: m.text == "🔓 Заявка на разбан")
def unban_request(message):
    user_states[message.chat.id] = 'unban'
    bot.send_message(
        message.chat.id,
        "🔓 <b>Заявка на разбан</b>\n\n"
        "Укажите в одном сообщении:\n"
        "- Ваш никнейм\n"
        "- Причину бана (если знаете)\n"
        "- Почему вас стоит разбанить\n\n"
        "Для отмены нажмите /start.",
        reply_markup=remove_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'unban')
def process_unban(message):
    user_states[message.chat.id] = None
    ticket_id = create_ticket(message.chat.id, "Разбан", message.text)
    
    admin_text = (
        f"🔓 <b>Заявка на разбан</b>\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: <code>{message.chat.id}</code>\n"
        f"Тикет: <b>{ticket_id}</b>\n\n"
        f"{message.text}"
    )
    
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, admin_text)
    
    bot.send_message(
        message.chat.id,
        f"✅ Заявка на разбан принята (тикет {ticket_id}). Ожидайте решения администрации.",
        reply_markup=main_keyboard()
    )

# ── Помощь / FAQ ──
@bot.message_handler(func=lambda m: m.text == "🆘 Помощь / FAQ")
def help_menu(message):
    bot.send_message(message.chat.id, "🆘 Часто задаваемые вопросы:", reply_markup=faq_keyboard())

# ── Связь с админом ──
@bot.message_handler(func=lambda m: m.text == "📞 Связь с админом")
def contact(message):
    user_states[message.chat.id] = 'contact'
    bot.send_message(
        message.chat.id,
        "📞 Вы перешли в режим связи с администрацией.\n"
        "Напишите ваш вопрос, и мы ответим в ближайшее время.\n"
        "Для выхода нажмите /start.",
        reply_markup=remove_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'contact')
def forward_contact(message):
    ticket_id = create_ticket(message.chat.id, "Обращение", message.text)
    
    admin_text = (
        f"📩 <b>Сообщение от пользователя</b>\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: <code>{message.chat.id}</code>\n"
        f"Тикет: <b>{ticket_id}</b>\n\n"
        f"{message.text}"
    )
    
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, admin_text)
    
    bot.send_message(message.chat.id, f"✅ Ваше сообщение отправлено администрации (тикет {ticket_id}). Ожидайте ответа.")

# ── Донат ──
@bot.message_handler(func=lambda m: m.text == "💰 Донат")
def donate_menu(message):
    bot.send_message(
        message.chat.id,
        "💰 <b>Донат на сервере BEST RUSSIA</b>\n\n"
        "Поддержите сервер и получите крутые привилегии!\n"
        "Выберите действие:",
        reply_markup=donate_keyboard()
    )

# ── Онлайн сервера ──
@bot.message_handler(func=lambda m: m.text == "👥 Онлайн сервера")
def server_online(message):
    # Заглушка. Можно подключить API сервера для реального онлайна
    bot.send_message(
        message.chat.id,
        "👥 <b>Статистика сервера</b>\n\n"
        f"🌍 IP: <code>{SERVER_IP}</code>\n"
        "🟢 Статус: <b>Работает</b>\n"
        "👤 Игроков онлайн: <b>127/500</b>\n"
        "📊 Uptime: <b>99.9%</b>\n\n"
        "Для точной информации зайдите в игру или Discord.",
    )

# ── Новости ──
@bot.message_handler(func=lambda m: m.text == "📰 Новости")
def news(message):
    bot.send_message(
        message.chat.id,
        f"📰 <b>Новости сервера BEST RUSSIA</b>\n\n"
        f"{server_news}\n\n"
        f"🔗 Discord: {DISCORD_LINK}\n"
        f"🔗 VK: {VK_LINK}"
    )

# ── Для новичков ──
@bot.message_handler(func=lambda m: m.text == "❓ Для новичков")
def newbie_guide(message):
    guide = (
        "❓ <b>Информация для новичков</b>\n\n"
        "🎮 <b>Как начать играть:</b>\n"
        f"1. Скачайте SA-MP 0.3.7-R1\n"
        f"2. Установите сборку модов из Discord\n"
        f"3. Подключитесь к серверу: <code>{SERVER_IP}</code>\n\n"
        "📋 <b>Первые шаги:</b>\n"
        "1. Изучите правила сервера\n"
        "2. Пройдите обучение у наставников\n"
        "3. Найдите работу и начните зарабатывать\n\n"
        "💡 <b>Советы:</b>\n"
        "- Слушайте опытных игроков\n"
        "- Не нарушайте правила\n"
        "- Играйте честно и получайте удовольствие!\n\n"
        f"Нужна помощь? Обратитесь в Discord: {DISCORD_LINK}"
    )
    bot.send_message(message.chat.id, guide)

# ── Админ-команды ──
@bot.message_handler(commands=['reply'])
def admin_reply(message):
    """Ответ пользователю: /reply <user_id> <текст>"""
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(message.chat.id, "❌ Использование: /reply <user_id> <текст>")
        return
    user_id, reply_text = parts[1], parts[2]
    try:
        bot.send_message(int(user_id), f"💬 <b>Ответ от администрации {SERVER_NAME}:</b>\n{reply_text}")
        bot.send_message(message.chat.id, f"✅ Ответ отправлен пользователю {user_id}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при отправке: {e}")

@bot.message_handler(commands=['close'])
def admin_close(message):
    """Закрыть тикет: /close <ticket_id>"""
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Использование: /close <ticket_id>")
        return
    ticket_id = parts[1]
    if ticket_id in tickets:
        tickets[ticket_id]["status"] = "closed"
        user_id = tickets[ticket_id]["user_id"]
        bot.send_message(int(user_id), f"🔒 Ваш тикет {ticket_id} закрыт. Если проблема осталась — создайте новый.")
        bot.send_message(message.chat.id, f"✅ Тикет {ticket_id} закрыт.")
    else:
        bot.send_message(message.chat.id, f"❌ Тикет {ticket_id} не найден.")

@bot.message_handler(commands=['tickets'])
def admin_tickets(message):
    """Список открытых тикетов."""
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    open_tickets = [(tid, t) for tid, t in tickets.items() if t["status"] == "open"]
    if not open_tickets:
        bot.send_message(message.chat.id, "📭 Нет открытых тикетов.")
        return
    text = "📋 <b>Открытые тикеты:</b>\n\n"
    for tid, t in open_tickets:
        text += f"<b>{tid}</b> | {t['type']} | {t['created']} | ID: {t['user_id']}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['setnews'])
def admin_set_news(message):
    """Изменить новость: /setnews <текст>"""
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    global server_news
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Использование: /setnews <текст новости>")
        return
    server_news = parts[1]
    bot.send_message(message.chat.id, f"✅ Новость обновлена:\n{server_news}")

# ── Inline-кнопки ──
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

@bot.callback_query_handler(func=lambda call: call.data == "donate_list")
def donate_list_callback(call):
    bot.answer_callback_query(call.id)
    text = (
        "💎 <b>Привилегии доната:</b>\n\n"
        "🥉 <b>Bronze</b> — 100₽\n"
        "- Удвоенный опыт\n"
        "- Зелёный цвет в чате\n\n"
        "🥈 <b>Silver</b> — 250₽\n"
        "- Всё из Bronze\n"
        "- Утроенный опыт\n"
        "- Своя машина\n\n"
        "🥇 <b>Gold</b> — 500₽\n"
        "- Всё из Silver\n"
        "- 5x опыт\n"
        "- Премиум скин\n"
        "- Доступ к /heal\n\n"
        f"Купить: {DONATE_LINK}"
    )
    bot.send_message(call.message.chat.id, text)

# ── Fallback ──
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
