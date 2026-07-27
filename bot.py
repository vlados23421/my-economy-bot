import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot import types
from supabase import create_client, Client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Загрузка настроек из Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

if not all([BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    logging.critical("Не все переменные окружения заданы на Render!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Фоновый веб-сервер для UptimeRobot
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Support Bot is running smoothly!")
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"🌐 Веб-сервер для UptimeRobot запущен на порту {port}")
    server.serve_forever()

# --- МЕНЮ И КЛАВИАТУРЫ ---

def get_start_keyboard():
    """Создает главное меню с кнопками"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    btn_ticket = types.InlineKeyboardButton(text="🚀 Создать обращение", callback_data="start_ticket")
    btn_faq = types.InlineKeyboardButton(text="❓ Частые вопросы (FAQ)", callback_data="open_faq")
    keyboard.add(btn_ticket, btn_faq)
    return keyboard

def get_faq_keyboard():
    """Создает меню часто задаваемых вопросов"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    btn_faq1 = types.InlineKeyboardButton(text="📥 Как скачать игру?", callback_data="faq_download")
    btn_faq2 = types.InlineKeyboardButton(text="🔒 Проблемы с донатом", callback_data="faq_donate")
    btn_back = types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")
    keyboard.add(btn_faq1, btn_faq2, btn_back)
    return keyboard

# --- ОБРАБОТЧИКИ КОМАНД ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"

    try:
        supabase.table("users").upsert({"id": user_id, "username": username}).execute()
        
        # Красивое стилизованное приветствие для проекта BEST RUSSIA
        welcome_text = (
            "🇷🇺 **ДОБРО ПОЖАЛОВАТЬ В ТЕХПОДДЕРЖКУ BEST RUSSIA!**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Приветствуем тебя, боец! Рады видеть тебя на нашем проекте. "
            "Этот бот создан для того, чтобы оперативно помогать игрокам "
            "в решении любых технических и игровых проблем.\n\n"
            "💡 **Чем мы можем помочь?**\n"
            "• Проблемы со входом или лаунчером\n"
            "• Ошибки при оплате в магазине доната\n"
            "• Баги, уязвимости или жалобы\n\n"
            "⚠️ **Важно:** Пожалуйста, описывайте проблему максимально подробно, "
            "чтобы администрация смогла помочь вам быстрее.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Выберите интересующее вас действие ниже 👇"
        )
        
        bot.send_message(
            message.chat.id, 
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка сохранения юзера {user_id}: {e}")
        bot.send_message(message.chat.id, "❌ Техническая ошибка базы данных. Попробуйте позже.")

# --- ОБРАБОТКА ИНЛАЙН-КНОПОК ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    # Кнопка создания тикета
    if call.data == "start_ticket":
        bot.delete_message(call.message.chat.id, call.message.message_id) # Удаляем старое меню для чистоты
        msg = bot.send_message(
            call.message.chat.id, 
            "👤 Step 1/2: **Введите ваш точный игровой никнейм на сервере:**",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_nickname)
        bot.answer_callback_query(call.id)
        
    # Кнопка открытия FAQ
    elif call.data == "open_faq":
        faq_text = (
            "❓ **БАЗА ЗНАНИЙ (FAQ) PROJECT BEST RUSSIA**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Прежде чем писать техподдержке, ознакомьтесь с частыми вопросами. "
            "Возможно, здесь уже есть решение вашей проблемы!"
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=faq_text,
            parse_mode="Markdown",
            reply_markup=get_faq_keyboard()
        )
        bot.answer_callback_query(call.id)
        
    # Кнопка возврата в меню
    elif call.data == "back_to_menu":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        cmd_start(call) # Вызываем стартовое приветствие заново
        bot.answer_callback_query(call.id)
        
    # Ответы на конкретные вопросы FAQ
    elif call.data == "faq_download":
        bot.send_message(call.message.chat.id, "📥 **Как скачать игру:**\nСкачать наш актуальный лаунчер можно на официальном сайте проекта (ссылка) или в нашей главной группе ВК. Инструкция по установке прикреплена там же.")
        bot.answer_callback_query(call.id)
        
    elif call.data == "faq_donate":
        bot.send_message(call.message.chat.id, "🔒 **Проблемы с донатом:**\nЕсли средства не поступили на игровой баланс в течение 15 минут, подготовьте чек оплаты (PDF или скриншот) и создайте обращение через кнопку «Создать обращение», выбрав этот пункт.")
        bot.answer_callback_query(call.id)
        
    # Кнопка закрытия тикета администрацией
    elif call.data.startswith('close_'):
        ticket_id = call.data.split('_')[1]
        try:
            supabase.table("tickets").update({"status": "closed"}).eq("id", ticket_id).execute()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n🔒 **Тикет закрыт администратором @{call.from_user.username}**",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, text="Тикет успешно закрыт!")
        except Exception as e:
            logging.error(f"Ошибка закрытия тикета {ticket_id}: {e}")
            bot.answer_callback_query(call.id, text="Ошибка работы с БД.")

# --- ПОШАГОВЫЙ СБОР ДАННЫХ ДЛЯ ТИКЕТА ---

def process_nickname(message):
    nickname = message.text
    user_id = message.from_user.id

    if not nickname or nickname.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Никнейм не может быть командой. Введите ваш игровой ник:")
        bot.register_next_step_handler(msg, process_nickname)
        return

    if len(nickname) > 32:
        msg = bot.send_message(message.chat.id, "⚠️ Слишком длинный никнейм. Попробуйте еще раз:")
        bot.register_next_step_handler(msg, process_nickname)
        return

    try:
        supabase.table("users").update({"nickname": nickname}).eq("id", user_id).execute()
        msg = bot.send_message(
            message.chat.id, 
            "📝 Step 2/2: **Опишите вашу проблему как можно подробнее.**\n\nЕсли есть скриншоты, загрузите их на фотохостинг (например, Imgur/Yapx) и прикрепите ссылку.",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_issue, nickname)
    except Exception as e:
        logging.error(f"Ошибка обновления ника для {user_id}: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Повторите команду /start.")

def process_issue(message, nickname):
    issue_text = message.text
    user_id = message.from_user.id

    if not issue_text or issue_text.startswith('/'):
        msg = bot.send_message(message.chat.id, "⚠️ Опишите проблему обычным текстом:")
        bot.register_next_step_handler(msg, process_issue, nickname)
        return

    if len(issue_text) > 1000:
        msg = bot.send_message(message.chat.id, "⚠️ Описание слишком длинное (макс. 1000 символов). Сократите текст:")
        bot.register_next_step_handler(msg, process_issue, nickname)
        return

    try:
        # Сохранение тикета в базу
        ticket_data = {"user_id": user_id, "text": issue_text, "status": "open"}
        response = supabase.table("tickets").insert(ticket_data).execute()
        
        ticket_id = "Новый"
        if response.data:
            ticket_id = response.data[0].get("id", "Новый") if isinstance(response.data, list) else response.data.get("id", "Новый")

        # Ответ пользователю
        bot.send_message(
            message.chat.id, 
            f"✅ **Ваше обращение принято!**\nНомер тикета: `#{ticket_id}`.\n\nАдминистрация BEST RUSSIA свяжется с вами в этом чате. Ожидайте ответа.",
            parse_mode="Markdown"
        )

        # Отправка в админ-чат
        if ADMIN_CHAT_ID:
            admin_msg = (
                f"🚨 **Новый тикет #{ticket_id}**\n"
                f"👤 **Игрок:** {nickname} (ID: `{user_id}`)\n"
                f" Telegram: @{message.from_user.username or 'отсутствует'}\n\n"
                f"📋 **Суть проблемы:**\n{issue_text}"
            )
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="❌ Закрыть тикет", callback_data=f"close_{ticket_id}"))
            
            bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown", reply_markup=keyboard)

 
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, text="Ошибка базы данных.")

