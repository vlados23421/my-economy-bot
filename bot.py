import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot import types

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# --- НАСТРОЙКИ ---
ADMIN_CHAT_ID = "8915047087"
BOT_TOKEN = "8957594048:AAHzRvyv9r1NssqlBlXYOZuujYcSVI2t20c"

# РЕЖИМ ТЕХ. РАБОТ: Измените на True, чтобы закрыть бота для всех игроков!
MAINTENANCE_MODE = False

user_cooldowns = {}
COOLDOWN_TIME = 600  
user_data_storage = {}  

bot = telebot.TeleBot(BOT_TOKEN)


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"BEST RUSSIA Support is active!")
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"🌐 Веб-сервер запущен на порту {port}")
    server.serve_forever()


# --- ПРОВЕРКА РЕЖИМА ТЕХ. РАБОТ ДЛЯ ВСЕХ КОМАНД ---
@bot.message_handler(func=lambda message: MAINTENANCE_MODE and message.chat.id != int(ADMIN_CHAT_ID))
def handle_maintenance(message):
    tech_text = (
        "🛠 **ВНИМАНИЕ! ТЕХНИЧЕСКИЕ РАБОТЫ**\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "Бот технической поддержки проекта **BEST RUSSIA** временно закрыт на техническое обслуживание.\n\n"
        "⚙️ Мы обновляем систему, чтобы помогать вам ещё быстрее. Совсем скоро мы снова откроемся, следите за новостями в канале!"
    )
    bot.send_message(message.chat.id, tech_text, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())


# --- КОМАНДА ДЛЯ АДМИНА ДЛЯ УПРАВЛЕНИЯ ТЕХ. РАБОТАМИ ---
@bot.message_handler(commands=['adminpanel'])
def cmd_adminpanel(message):
    if message.chat.id == int(ADMIN_CHAT_ID):
        keyboard = types.InlineKeyboardMarkup()
        if MAINTENANCE_MODE:
            keyboard.add(types.InlineKeyboardButton("🟢 Открыть бота для игроков", callback_data="set_work_open"))
        else:
            keyboard.add(types.InlineKeyboardButton("🔴 Закрыть бота на тех. работы", callback_data="set_work_close"))
            
        status = "❌ ЗАКРЫТ НА ТЕХ. РАБОТЫ" if MAINTENANCE_MODE else "🟢 РАБОТАЕТ В ШТАТНОМ РЕЖИМЕ"
        bot.send_message(ADMIN_CHAT_ID, f"🎛 **Панель управления BEST RUSSIA**\n Текущий статус бота: *{status}*", parse_mode="Markdown", reply_markup=keyboard)


# --- ОБРАБОТКА НАЖАТИЯ АДМИН-КНОПОК ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_work_'))
def handle_admin_panel_callback(call):
    global MAINTENANCE_MODE
    if call.message.chat.id == int(ADMIN_CHAT_ID):
        action = call.data.split('_')[-1]
        
        if action == "close":
            MAINTENANCE_MODE = True
            bot.edit_message_text("🛠 **Бот успешно закрыт на тех. работы!**\nТеперь обычные игроки при любом нажатии будут видеть сообщение о тех. работах.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        elif action == "open":
            MAINTENANCE_MODE = False
            bot.edit_message_text("🟢 **Бот успешно открыт в штатном режиме!**\nИгроки снова могут создавать тикеты и читать FAQ.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.answer_callback_query(call.id)


# --- КОМАНДА /START И ГЛАВНОЕ МЕНЮ ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    send_welcome_menu(message.chat.id, message.from_user.username)


def send_welcome_menu(chat_id, username=None):
    name = username or "Игрок"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_support = types.KeyboardButton("🚨 Создать обращение")
    btn_faq = types.KeyboardButton("ℹ️ Часто задаваемые вопросы")
    btn_resources = types.KeyboardButton("🌐 Наши ресурсы")
    markup.add(btn_support, btn_faq, btn_resources)

    welcome_text = (
        f"🇷🇺 **Добро пожаловать на проект BEST RUSSIA!**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"Приветствуем тебя, *{name}*! Это официальный бот технической поддержки нашего сервера.\n\n"
        f"🛠 Здесь ты можешь сообщить о баге, подать жалобу или задать вопрос администрации.\n\n"
        f"👇 Чтобы продолжить, выбери нужное действие на панели кнопками ниже:"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=markup)


# --- ПРОВЕРКА РЕЖИМА ТЕХ. РАБОТ ДЛЯ ВСЕХ ОСТАЛЬНЫХ НАЖАТИЙ ---
@bot.message_handler(func=lambda message: MAINTENANCE_MODE and message.chat.id != int(ADMIN_CHAT_ID))
def handle_maintenance(message):
    tech_text = (
        "🛠 **ВНИМАНИЕ! ТЕХНИЧЕСКИЕ РАБОТЫ**\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "Бот технической поддержки проекта **BEST RUSSIA** временно закрыт на техническое обслуживание.\n\n"
        "⚙️ Мы обновляем систему, чтобы помогать вам ещё быстрее. Совсем скоро мы снова откроемся, следите за новостями в канале!"
    )
    bot.send_message(message.chat.id, tech_text, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())


# --- ОБРАБОТКА МЕНЮ ДЛЯ ИГРОКОВ ---
@bot.message_handler(func=lambda message: message.text in ["🚨 Создать обращение", "ℹ️ Часто задаваемые вопросы", "🌐 Наши ресурсы"])
def handle_menu(message):
    user_id = message.from_user.id

    if message.text == "🚨 Создать обращение":
        current_time = time.time()
        if user_id in user_cooldowns:
            time_passed = current_time - user_cooldowns[user_id]
            if time_passed < COOLDOWN_TIME:
                time_left = int(COOLDOWN_TIME - time_passed)
                bot.send_message(
                    message.chat.id, 
                    f"⚠️ **Антифлуд система!**\nПодать новое обращение можно через: `{time_left // 60} мин. {time_left % 60} сек.`",
                    parse_mode="Markdown"
                )
                return

        user_data_storage[user_id] = {"nickname": "Не указан", "category": "Не указана"}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("❌ Отмена"))
        
        msg = bot.send_message(
            message.chat.id, 
            "👤 **Шаг 1 из 2:** Введите ваш точный игровой никнейм (например, `Ivan_Ivanov`):\n\n_Если передумали, нажмите кнопку «❌ Отмена» ниже._",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_nickname)
        
    elif message.text == "ℹ️ Часто задаваемые вопросы":
        faq_text = (
            "📌 **Популярные вопросы и ответы:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "📱 **Проблемы с лаунчером и сборкой:**\n➡️ Нажмите кнопку 'Починить игру' в лаунчере или удалите сторонние клео-скрипты.\n\n"
            "🎮 **Игровой процесс:**\n➡️ Устроиться на работу можно в Центре занятости (`/gps`). Жалобы на админов оставляйте в группе ВК.\n\n"
            "💳 **Проблемы с донатом:**\n➡️ Обработка платежа занимает до 15 минут. Если донат не пришел, создайте обращение в этом боте."
        )
        bot.send_message(message.chat.id, faq_text, parse_mode="Markdown")

    elif message.text == "🌐 Наши ресурсы":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("📢 Телеграм канал проекта", url="https://t.me/BestRPSueta"),
            types.InlineKeyboardButton("🇷🇺 Лаборатория разработчиков", url="https://t.me/DevelopmentSiteMe")
        )
        bot.send_message(message.chat.id, "🌐 **Официальные ресурсы проекта BEST RUSSIA:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nПодписывайтесь! 👇", reply_markup=keyboard)


def process_nickname(message):
    if message.text == "❌ Отмена":
        send_welcome_menu(message.chat.id, message.from_user.username)
        return
    nickname = message.text
    if not nickname or nickname.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Никнейм не может быть командой. Введите игровой ник:")
        bot.register_next_step_handler(msg, process_nickname)
        return
    msg = bot.send_message(message.chat.id, f"📝 **Шаг 2 из 2:** Отлично, `{nickname}`. Теперь подробно опишите вашу проблему текстом:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_issue, nickname)


def process_issue(message, nickname):
    if message.text == "❌ Отмена":
        send_welcome_menu(message.chat.id, message.from_user.username)
        return
    issue_text = message.text
    user_id = message.from_user.id
    if not issue_text or issue_text.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Опишите проблему обычным текстом:")
        bot.register_next_step_handler(msg, process_issue, nickname)
        return

    user_cooldowns[user_id] = time.time()
    send_welcome_menu(message.chat.id, message.from_user.username)
    bot.send_message(message.chat.id, "✅ **Ваше обращение успешно отправлено администрации BEST RUSSIA! Ожидайте ответа.**")

    admin_msg = (
        f"🚨 **НОВЫЙ ТИКЕТ ПОДДЕРЖКИ**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"👤 **Игрок:** `{nickname}`\n📱 **Профиль:** @{message.from_user.username or 'скрыт'}\n\n"
        f"📋 **Суть проблемы:**\n_{issue_text}_\n\n⚙️ `id_user:{user_id}`"
    )
    bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.chat.id == int(ADMIN_CHAT_ID) and message.reply_to_message is not None)
def handle_admin_reply(message):
    try:
        reply_text = message.reply_to_message.text
        if "⚙️ id_user:" in reply_text:
            target_user_id = reply_text.split("⚙️ id_user:")[-1].strip()
            user_msg = f"✉️ **Ответ от администрации BEST RUSSIA:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n{message.text}"
            bot.send_message(target_user_id, user_msg, parse_mode="Markdown")
            bot.send_message(ADMIN_CHAT_ID, f"✅ Ответ успешно доставлен игроку (ID: `{target_user_id}`)!")
    except Exception as e:
        logging.error(f"Ошибка при ответе админа: {e}")
        bot.send_message(ADMIN_CHAT_ID, f"❌ Ошибка отправки ответа: {e}")


def run_bot_polling():
    logging.info("🚀 Бот BEST RUSSIA запущен в фоновом режиме...")
    bot.infinity_polling()


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    run_web_server()
