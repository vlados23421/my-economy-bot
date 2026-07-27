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
# Ваш ID админа. Бот будет пересылать все тикеты напрямую вам
ADMIN_CHAT_ID = "8915047087"

# Вставьте сюда ваш токен от @BotFather
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


# --- ОБРАБОТКА ОСНОВНОГО МЕНЮ ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🚨 Создать обращение":
        msg = bot.send_message(
            message.chat.id, 
            "👤 **Шаг 1 из 2:** Введите ваш точный игровой никнейм (например, `Ivan_Ivanov`):",
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
    else:
        bot.send_message(message.chat.id, "⚠️ Используйте кнопки в меню для управления ботом.")


# --- СБОР ДАННЫХ ТИКЕТА БЕЗ БД ---
def process_nickname(message):
    nickname = message.text

    if not nickname or nickname.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Никнейм не может быть системной командой. Введите игровой ник:")
        bot.register_next_step_handler(msg, process_nickname)
        return

    msg = bot.send_message(
        message.chat.id, 
        "📝 **Шаг 2 из 2:** Опишите вашу проблему как можно подробнее.\n\n"
        "💡 _Если у вас есть скриншот или видео, залейте его на фотохостинг и вставьте ссылку в текст сообщения._",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_issue, nickname)


def process_issue(message, nickname):
    issue_text = message.text
    user_id = message.from_user.id

    if not issue_text or issue_text.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Опишите проблему обычным текстом:")
        bot.register_next_step_handler(msg, process_issue, nickname)
        return

    # 1. Уведомление игрока
    success_text = (
        f"✅ **Ваше обращение успешно отправлено!**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"Администрация BEST RUSSIA уже получила уведомление и скоро свяжется с вами. Ожидайте."
    )
    return_to_menu(message, success_text)

    # 2. Мгновенная пересылка админу (вам в ЛС) напрямую в Telegram
    admin_msg = (
        f"🚨 **НОВЫЙ ТИКЕТ ПОДДЕРЖКИ**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"👤 **Игрок:** `{nickname}`\n"
        f"🆔 **Telegram ID:** `{user_id}`\n"
        f"📱 **Профиль:** @{message.from_user.username or 'скрыт'}\n\n"
        f"📋 **Суть проблемы:**\n_{issue_text}_"
    )
    
    bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown")


def return_to_menu(message, text):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🚨 Создать обращение"), types.KeyboardButton("ℹ️ Часто задаваемые вопросы"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


# --- ЗАПУСК ПОТОКОВ ---
if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logging.info("🚀 Бот BEST RUSSIA успешно запущен без базы данных...")
    bot.infinity_polling()
