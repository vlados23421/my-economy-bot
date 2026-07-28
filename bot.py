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
BOT_TOKEN = "8957594048:AAHKkvlMHKVEQcZ0awDDWtpD6F37LGrp9lE"

user_cooldowns = {}
COOLDOWN_TIME = 600  # 10 минут кулдауна на тикеты

bot = telebot.TeleBot(BOT_TOKEN)


# --- ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT ---
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
    logging.info(f"🌐 Сервер UptimeRobot запущен на порту {port}")
    server.serve_forever()


# --- КОМАНДА /START И ГЛАВНОЕ МЕНЮ ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    send_welcome_menu(message.chat.id, message.from_user.username)


def send_welcome_menu(chat_id, username=None):
    name = username or "Игрок"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_support = types.KeyboardButton("🚨 Создать обращение")
    btn_faq = types.KeyboardButton("ℹ️ Часто задаваемые вопросы")
    btn_status = types.KeyboardButton("📊 Статус сервера")
    btn_resources = types.KeyboardButton("🌐 Наши ресурсы")
    markup.add(btn_support, btn_faq, btn_status, btn_resources)

    welcome_text = (
        f"🇷🇺 **Добро пожаловать на проект BEST RUSSIA!**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"Приветствуем тебя, *{name}*! Это официальный бот технической поддержки нашего сервера.\n\n"
        f"🛠 Здесь ты можешь сообщить о баге, подать жалобу или задать вопрос администрации.\n\n"
        f"👇 Чтобы продолжить, выбери нужное действие на панели кнопками ниже:"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=markup)


# --- ОБРАБОТКА МЕНЮ ДЛЯ ИГРОКОВ ---
@bot.message_handler(func=lambda message: message.chat.id != int(ADMIN_CHAT_ID) and message.text in ["🚨 Создать обращение", "ℹ️ Часто задаваемые вопросы", "🌐 Наши ресурсы", "📊 Статус сервера"])
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

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("❌ Отмена"))
        
        msg = bot.send_message(
            message.chat.id, 
            "👤 **Шаг 1 из 3:** Введите ваш точный игровой никнейм (например, `Ivan_Ivanov`):\n\n"
            "_Если передумали, нажмите кнопку «❌ Отмена» ниже._",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_nickname)
        
    elif message.text == "ℹ️ Часто задаваемые вопросы":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("📱 1. Лаунчер и Сборка", callback_data="faq_launcher"),
            types.InlineKeyboardButton("🎮 2. Игровой процесс", callback_data="faq_gameplay"),
            types.InlineKeyboardButton("💳 3. Донат и Магазин", callback_data="faq_donate"),
            types.InlineKeyboardButton("📜 4. Правила и Жалобы", callback_data="faq_rules")
        )
        bot.send_message(
            message.chat.id, 
            "📂 **Выберите интересующий раздел часто задаваемых вопросов:**", 
            reply_markup=keyboard
        )

    elif message.text == "📊 Статус сервера":
        status_text = (
            "📊 **Статус серверов проекта BEST RUSSIA:**\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "🟢 **Основной сервер:** `ОФФЛАЙН`\n"
            "🛠 **Лаунчер и автообновления:** `Не доступно`\n\n"
            "🔗 **IP Адрес для подключения:** `play.bestrussia-rp.ru:7777`\n"
            "💡 _Если вы не можете зайти на сервер, проверьте стабильность вашего интернет-соединения или перезагрузите лаунчер._"
        )
        bot.send_message(message.chat.id, status_text, parse_mode="Markdown")

    elif message.text == "🌐 Наши resources":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("📢 Телеграм канал проекта", url="https://t.me/BestRPSueta"),
            types.InlineKeyboardButton("🇷🇺 Официальное сообщество ВК", url="https://vk.ru/bestrussiaonlinerp")
        )
        bot.send_message(
            message.chat.id, 
            "🌐 **Официальные ресурсы проекта BEST RUSSIA:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nПодписывайтесь, чтобы первыми узнавать о новостях! 👇", 
            reply_markup=keyboard
        )


# --- ИНЛАЙН ОБРАБОТЧИК ДЛЯ FAQ И ОЦЕНОК ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # Разделы FAQ
    if call.data.startswith("faq_"):
        section = call.data.split("_")[1]
        faq_response = ""
        
        if section == "launcher":
            faq_response = (
                "📱 **Проблемы с лаунчером и сборкой:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "• **Ошибка 'Файлы повреждены'**: Откройте лаунчер и нажмите кнопку 'Починить игру' в настройках.\n"
                "• **Белый экран при запуске**: Обновите драйверы видеокарты и установите чистый DirectX.\n"
                "• **Крашит при заходе**: Удалите сторонние модификации или клео-скрипты, если вы их ставили."
            )
        elif section == "gameplay":
            faq_response = (
                "🎮 **Вопросы по игровому процессу:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "• **Как устроиться на работу?**: Используйте GPS-навигатор (`/gps`) -> Важные места -> Центр занятости.\n"
                "• **Где получить права?**: Получить водительские права можно в Автошколе (`/gps` -> Автошкола).\n"
                "• **Меня забанили/посадили ни за что**: Оставьте официальную жалобу на администратора в нашей группе ВК."
            )
        elif section == "donate":
            faq_response = (
                "💳 **Проблемы с донатом и магазином:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "• **Донат не пришел в игру**: Платежи обрабатываются до 15 минут. Если время прошло, создайте тикет в этом боте и прикрепите чек.\n"
                "• **Как активировать донат-код?**: Введите команду `/donate` на сервере в игре и выберите пункт 'Активация'."
            )
        elif section == "rules":
            faq_response = (
                "📜 **Правила сервера и игровой процесс:**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "• **Ознакомиться с правилами** можно в закрепленных сообщениях нашего Discord или сообщества ВК.\n"
                "• **Запрещено**: DM (убийство без причины), DB (убийство машиной), SK (спавн килл), Оскорбление родных.\n"
                "• Помните, что за серьезные нарушения ваш аккаунт может быть заблокирован навсегда."
            )
            
        bot.send_message(call.message.chat.id, faq_response, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    # Выбор категории тикета
    elif call.data.startswith('cat:'):
        data_parts = call.data.split(':', 2)
        category, nickname = data_parts[1], data_parts[2]
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

        cat_emoji = "❓"
        if category == "баг": cat_emoji = "🐛 [БАГ / ОШИБКА]"
        elif category == "жалоба": cat_emoji = "🦅 [ЖАЛОБА]"
        elif category == "донат": cat_emoji = "💳 [ДОНАТ]"
        elif category == "другое": cat_emoji = "💬 [ОБЩИЙ ВОПРОС]"

        msg = bot.send_message(
            call.message.chat.id, 
            f"📝 **Шаг 3 из 3:** Вы выбрали категорию: *{cat_emoji}*.\n\nТеперь подробно опишите вашу проблему текстом.",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_issue, nickname, cat_emoji)
        bot.answer_callback_query(call.id)

    # Обработка оценки администратора игроком
    elif call.data.startswith('rate:'):
        stars, admin_id = call.data.split(':')[1], call.data.split(':')[2]
        # Скрываем кнопки у игрока после нажатия
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "❤️ Спасибо за вашу оценку! Вы помогаете делать BEST RUSSIA лучше.")
        
        # Отправляем лог оценки вам в личку
        bot.send_message(
            admin_id, 
            f"📊 **Новый отзыв о работе администрации!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n👤 Игрок поставил оценку: {stars} из 5 звёзд! ⭐"
        )
        bot.answer_callback_query(call.id)


# --- СБОР ДАННЫХ ТИКЕТА ---
def process_nickname(message):
    if message.text == "❌ Отмена":
        send_welcome_menu(message.chat.id, message.from_user.username)
        return
    nickname = message.text
    if not nickname or nickname.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Никнейм не может быть командой. Введите игровой ник:")
        bot.register_next_step_handler(msg, process_nickname)
        return
