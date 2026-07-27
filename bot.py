import os
import logging
import threading
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
    username = message.from_user.username or "Игрок"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_support = types.KeyboardButton("🚨 Создать обращение")
    btn_faq = types.KeyboardButton("ℹ️ Часто задаваемые вопросы")
    markup.add(btn_support, btn_faq)

    welcome_text = (
        f"🇷🇺 **Добро пожаловать на проект BEST RUSSIA!**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"Приветствуем тебя, *{username}*! Это официальный бот технической поддержки нашего сервера.\n\n"
        f"🛠 Здесь ты можешь сообщить о баге, подать жалобу или задать вопрос администрации.\n\n"
        f"👇 Чтобы продолжить, выбери нужное действие на панели кнопками ниже:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)


# --- ОБРАБОТКА МЕНЮ ДЛЯ ИГРОКОВ ---
@bot.message_handler(func=lambda message: message.chat.id != int(ADMIN_CHAT_ID) and message.text in ["🚨 Создать обращение", "ℹ️ Часто задаваемые вопросы"])
def handle_menu(message):
    if message.text == "🚨 Создать обращение":
        msg = bot.send_message(
            message.chat.id, 
            "👤 **Шаг 1 из 3:** Введите ваш точный игровой никнейм (например, `Ivan_Ivanov`):",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_nickname)
        
    elif message.text == "ℹ️ Часто задаваемые вопросы":
        faq_text = (
            "📌 **Популярные вопросы и ответы:**\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "❓ **Как начать играть?**\n"
            "➡️ Скачайте наш лаунчер по официальной ссылке в нашей группе VK.\n\n"
            "❓ **Я застрял или провалился под текстуры?**\n"
            "➡️ Напишите в игре команду `/report` в репорт сервера, свободный администратор сразу вам поможет.\n\n"
            "❓ **Проблемы с донатом?**\n"
            "➡️ Если платеж не пришел в течение часа, создайте обращение через этот бот, прикрепив чек."
        )
        bot.send_message(message.chat.id, faq_text, parse_mode="Markdown")


# --- СБОР ДАННЫХ: НИКНЕЙМ ---
def process_nickname(message):
    nickname = message.text

    if not nickname or nickname.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Никнейм не может быть системной командой. Введите игровой ник:")
        bot.register_next_step_handler(msg, process_nickname)
        return

    # Создаем инлайн-кнопки для выбора категории проблемы
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn_bug = types.InlineKeyboardButton("🐛 Нашел баг / ошибку", callback_data=f"cat:баг:{nickname}")
    btn_report = types.InlineKeyboardButton("🦅 Жалоба на игрока/админа", callback_data=f"cat:жалоба:{nickname}")
    btn_donat = types.InlineKeyboardButton("💳 Проблема с донатом", callback_data=f"cat:донат:{nickname}")
    btn_other = types.InlineKeyboardButton("❓ Другой вопрос", callback_data=f"cat:другое:{nickname}")
    
    keyboard.add(btn_bug, btn_report, btn_donat, btn_other)

    bot.send_message(
        message.chat.id, 
        f"📋 **Шаг 2 из 3:** Отлично, `{nickname}`. Теперь выберите категорию вашего обращения ниже:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# --- ОБРАБОТКА ВЫБОРА КАТЕГОРИИ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('cat:'))
def handle_category_choice(call):
    # Разделяем по двоеточию, чтобы избежать багов с нижним подчёркиванием в никнеймах
    data_parts = call.data.split(':', 2)
    category = data_parts[1]
    nickname = data_parts[2]

    # Убираем инлайн-кнопки у старого сообщения
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    # Присваиваем красивый статус-смайлик для админа
    cat_emoji = "❓"
    if category == "баг": cat_emoji = "🐛 [БАГ / ОШИБКА]"
    elif category == "жалоба": cat_emoji = "🦅 [ЖАЛОБА]"
    elif category == "донат": cat_emoji = "💳 [ДОНАТ]"
    elif category == "другое": cat_emoji = "💬 [ОБЩИЙ ВОПРОС]"

    msg = bot.send_message(
        call.message.chat.id, 
        f"📝 **Шаг 3 из 3:** Вы выбрали категорию: *{cat_emoji}*.\n\n"
        f"Теперь подробно опишите вашу проблему текстом. Если есть скриншоты, укажите ссылку на них.",
        parse_mode="Markdown"
    )
    # Передаем в следующий шаг никнейм и выбранную категорию
    bot.register_next_step_handler(msg, process_issue, nickname, cat_emoji)
    bot.answer_callback_query(call.id)


# --- СБОР ДАННЫХ: СУТЬ ПРОБЛЕМЫ И ОТПРАВКА ---
def process_issue(message, nickname, category_title):
    issue_text = message.text
    user_id = message.from_user.id

    if not issue_text or issue_text.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Опишите проблему обычным текстом:")
        bot.register_next_step_handler(msg, process_issue, nickname, category_title)
        return

    success_text = (
        f"✅ **Ваше обращение успешно отправлено!**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"Категория: *{category_title}*\n\n"
        f"Администрация BEST RUSSIA уже получила уведомление и скоро свяжется с вами. Ожидайте."
    )
    return_to_menu(message, success_text)

    # Отправляем оформленный тикет вам (админу) с указанием категории
    admin_msg = (
        f"🚨 **НОВЫЙ ТИКЕТ ПОДДЕРЖКИ**\n"
        f"📁 **Категория:** {category_title}\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"👤 **Игрок:** `{nickname}`\n"
        f"📱 **Профиль:** @{message.from_user.username or 'скрыт'}\n\n"
        f"📋 **Суть проблемы:**\n_{issue_text}_\n\n"
        f"⚙️ `id_user:{user_id}`"
    )
    
    bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown")


def return_to_menu(message, text):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🚨 Создать обращение"), types.KeyboardButton("ℹ️ Часто задаваемые вопросы"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


# --- ФУНКЦИЯ ОТВЕТА ИГРОКУ ОТ АДМИНА ЧЕРЕЗ REPLY ---
@bot.message_handler(func=lambda message: message.chat.id == int(ADMIN_CHAT_ID) and message.reply_to_message is not None)
def handle_admin_reply(message):
    try:
        reply_text = message.reply_to_message.text
        
        if "⚙️ id_user:" in reply_text:
            target_user_id = reply_text.split("⚙️ id_user:")[-1].strip()
            admin_answer = message.text
            
            user_msg = (
                f"✉️ **Ответ от администрации BEST RUSSIA:**\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"{admin_answer}"
            )
            
            bot.send_message(target_user_id, user_msg, parse_mode="Markdown")
            bot.send_message(ADMIN_CHAT_ID, f"✅ Ответ успешно доставлен игроку (ID: `{target_user_id}`)!")
            
    except Exception as e:
        logging.error(f"Ошибка при пересылке ответа админа: {e}")
        bot.send_message(ADMIN_CHAT_ID, f"❌ Не удалось доставить ответ. Ошибка: {e}")


# --- ЗАПУСК ПОТОКОВ ---
if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logging.info("🚀 Прокачанный бот BEST RUSSIA успешно запущен...")
    bot.infinity_polling()
