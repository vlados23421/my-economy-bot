import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot import types
from supabase import create_client, Client

# Настройка логирования для вывода ошибок в панель Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# --- НАСТРОЙКИ И ПЕРЕМЕННЫЕ (ФИНАЛЬНЫЙ ВАРИАНТ) ---
ADMIN_CHAT_ID = "8915047087"
SUPABASE_URL = "https://supabase.co"
SUPABASE_KEY = "sb_publishable_8WXX1OgOJ7Vn92CWFI5MXQ_dLxjfNa3"
# Вставьте сюда ваш токен от @BotFather (например: "123456789:ABCdef...")
BOT_TOKEN = "8957594048:AAFMQMbt2J5eDPxZZ2RBner-OWnMMpDnCG0"

# Валидация токена перед инициализацией
if not BOT_TOKEN or "BOTFATHER" in BOT_TOKEN:
    logging.critical("💥 КРИТИЧЕСКАЯ ОШИБКА: Вы забили заменить заглушку на реальный токен от BotFather!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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
    user_id = message.from_user.id
    username = message.from_user.username or "Игрок"

    try:
        supabase.table("users").upsert({"id": user_id, "username": username}).execute()
        
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
    except Exception as e:
        logging.error(f"Ошибка при старте {user_id}: {e}")
        bot.send_message(message.chat.id, "❌ Произошла техническая ошибка. Пожалуйста, попробуйте позже.")


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


# --- СБОР ДАННЫХ ТИКЕТА ---
def process_nickname(message):
    nickname = message.text
    user_id = message.from_user.id

    if not nickname or nickname.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Никнейм не может быть системной командой. Введите игровой ник:")
        bot.register_next_step_handler(msg, process_nickname)
        return

    try:
        supabase.table("users").update({"nickname": nickname}).eq("id", user_id).execute()
        
        msg = bot.send_message(
            message.chat.id, 
            "📝 **Шаг 2 из 2:** Опишите вашу проблему как можно подробнее.\n\n"
            "💡 _Если у вас есть скриншот или видео, залейте его на фотохостинг и вставьте ссылку в текст сообщения._",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_issue, nickname)
    except Exception as e:
        logging.error(f"Ошибка сохранения ника {user_id}: {e}")
        return_to_menu(message, "❌ Ошибка сохранения данных. Возвращаем в меню.")


def process_issue(message, nickname):
    issue_text = message.text
    user_id = message.from_user.id

    if not issue_text or issue_text.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Опишите проблему обычным текстом:")
        bot.register_next_step_handler(msg, process_issue, nickname)
        return

    try:
        # 1. Сохранение в Supabase
        ticket_data = {"user_id": user_id, "text": issue_text, "status": "open"}
        response = supabase.table("tickets").insert(ticket_data).execute()
        
        ticket_id = response.data[0].get("id") if response.data else "Новый"

        # 2. Уведомление игрока
        success_text = (
            f"✅ **Ваше обращение принято!**\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"• **Номер тикета:** `#{ticket_id}`\n"
            f"• **Статус:** В очереди на рассмотрение\n\n"
            f"Администрация BEST RUSSIA уже получила уведомление и ответит вам прямо в этом чате. Ожидайте."
        )
        return_to_menu(message, success_text)

        # 3. Отправка уведомления вам (админу)
        if ADMIN_CHAT_ID:
            admin_msg = (
                f"🚨 **НОВЫЙ ТИКЕТ #{ticket_id}**\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"👤 **Игрок:** `{nickname}`\n"
                f"🆔 **Telegram ID:** `{user_id}`\n"
                f"📱 **Профиль:** @{message.from_user.username or 'скрыт'}\n\n"
                f"📋 **Суть проблемы:**\n_{issue_text}_"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="❌ Закрыть тикет", callback_data=f"close_{ticket_id}"))
            
            bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown", reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Ошибка отправки тикета {user_id}: {e}")
        return_to_menu(message, "❌ Ошибка при отправке тикета. Попробуйте позже.")


def return_to_menu(message, text):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🚨 Создать обращение"), types.KeyboardButton("ℹ️ Часто задаваемые вопросы"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


# --- КНОПКА ЗАКРЫТИЯ ДЛЯ АДМИНА ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('close_'))
def handle_close_ticket(call):
    ticket_id = call.data.split('_')[1]
    try:
        supabase.table("tickets").update({"status": "closed"}).eq("id", ticket_id).execute()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + f"\n\n🔒 **Тикет успешно закрыт и архивирован.**",
            reply_markup=None
        )
        bot.answer_callback_query(call.id, text="Тикет закрыт!")
    except Exception as e:
        logging.error(f"Ошибка закрытия тикета {ticket_id}: {e}")
        bot.answer_callback_query(call.id, text="Ошибка базы данных.")


# --- ЗАПУСК ПОТОКОВ С ЗАЩИТОЙ ОТ ПАДЕНИЙ ---
if __name__ == "__main__":
    try:
        # 1. Запуск веб-сервера для UptimeRobot
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()

        # 2. Запуск бота
        logging.info("🚀 Бот BEST RUSSIA успешно запущен и готов к работе...")
        bot.infinity_polling()
        
    except Exception as fatal_error:
        logging.critical(f"💥 КРИТИЧЕСКИЙ СБОЙ ПРИ ЗАПУСКЕ БОТА: {fatal_error}", exc_info=True)
