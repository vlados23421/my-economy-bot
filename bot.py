import os
import sys
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional

import telebot
from telebot import types
from flask import Flask, request, abort

# ─────────────────────────── Конфигурация ───────────────────────────
@dataclass
class Config:
    """Централизованные настройки приложения."""
    BOT_TOKEN: str = os.environ.get("8992162127:AAH-FF5MtWhahVBeNufUn7KXnQllb9MS-tA", "")
    ADMIN_CHAT_ID: str = os.environ.get("8718572838", "")
    WEBHOOK_URL: str = os.environ.get("https://my-economy-bot.onrender.com", "")

    # Серверные константы
    SERVER_IP: str = "188.127.241.74:3635"
    SERVER_NAME: str = "BEST RUSSIA"
    DISCORD_LINK: str = "https://discord.gg/qqHqy3mGg"
    VK_LINK: str = "https://vk.ru/bestrussiaonlinerp"

    # Проверка обязательных переменных
    def __post_init__(self):
        if not self.BOT_TOKEN:
            logging.critical("BOT_TOKEN не задан!")
            sys.exit(1)
        if not self.ADMIN_CHAT_ID:
            logging.warning("ADMIN_CHAT_ID не задан — административные уведомления не будут отправляться.")

config = Config()

# ─────────────────────────── Состояния пользователя ───────────────────────────
class UserState(str, Enum):
    """Состояния диалога с пользователем."""
    MAKING_COMPLAINT = "making_complaint"
    WAITING_FOR_ADMIN = "waiting_for_admin"

# ─────────────────────────── Тексты и контент ───────────────────────────
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
        "2. Запрещён PowerGaming (PG) — навязывание действий без возможности ответа.\n"
        "3. Запрещён Metagaming (MG) — использование OOC информации в IC.\n"
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
    "join": f"🌐 Чтобы зайти на сервер, запустите SA-MP, добавьте IP <code>{config.SERVER_IP}</code> в избранное и подключитесь.",
    "crash": (
        "🔧 <b>Не заходит в игру / ошибка</b>\n\n"
        "- Убедитесь, что установлен SA-MP 0.3.7-R1.\n"
        "- Скачайте нашу сборку модов (есть в Discord).\n"
        "- Проверьте антивирус, он может блокировать файлы.\n"
        "- Если проблема осталась — обратитесь в техподдержку."
    ),
    "unban": (
        "🔓 <b>Как получить разбан?</b>\n\n"
        "Заявки на разбан подаются через Discord в канале #разбан.\n"
        "Постоянные баны обсуждаются только с Главным Администратором."
    ),
    "mods": (
        "📦 <b>Где скачать сборку?</b>\n\n"
        f"Актуальная сборка всегда доступна в нашем Discord: {config.DISCORD_LINK}\n"
        "А также на официальном сайте."
    ),
    "progress": (
        "💾 <b>Потерял прогресс / вещи</b>\n\n"
        "Потеря могла произойти из-за вайпа, бага или санкций.\n"
        "Напишите в поддержку, указав никнейм и примерную дату. Мы проверим логи."
    ),
}

# ─────────────────────────── Бот ───────────────────────────
class SupportBot:
    """Основной класс бота поддержки."""
    def __init__(self, token: str, admin_chat_id: str):
        self.bot = telebot.TeleBot(token, parse_mode="HTML")
        self.admin_chat_id = admin_chat_id
        # user_id -> UserState или None
        self.user_states: Dict[int, Optional[UserState]] = {}

        self._register_handlers()

    def _register_handlers(self):
        """Регистрация всех обработчиков."""
        # Команды
        self.bot.message_handler(commands=['start'])(self.handle_start)

        # Текстовые кнопки главного меню
        self.bot.message_handler(func=lambda m: m.text == "📋 Правила")(self.show_rules)
        self.bot.message_handler(func=lambda m: m.text == "🌐 IP сервера")(self.show_ip)
        self.bot.message_handler(func=lambda m: m.text == "📝 Подать жалобу")(self.start_complaint)
        self.bot.message_handler(func=lambda m: m.text == "🆘 Помощь / FAQ")(self.show_faq)
        self.bot.message_handler(func=lambda m: m.text == "📞 Связаться с администрацией")(self.contact_admin)

        # Состояния
        self.bot.message_handler(func=lambda m: self.user_states.get(m.chat.id) == UserState.MAKING_COMPLAINT)(self.process_complaint)
        self.bot.message_handler(func=lambda m: self.user_states.get(m.chat.id) == UserState.WAITING_FOR_ADMIN)(self.forward_to_admin)

        # Inline-кнопки
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("rules_"))(self.handle_rules_callback)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("faq_"))(self.handle_faq_callback)

        # Команда администратора
        self.bot.message_handler(commands=['reply'])(self.admin_reply)

        # Fallback
        self.bot.message_handler(func=lambda m: True)(self.fallback)

    # ── Главное меню и клавиатуры ──
    def main_keyboard(self) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📋 Правила", "🌐 IP сервера")
        markup.add("📝 Подать жалобу", "🆘 Помощь / FAQ")
        markup.add("📞 Связаться с администрацией")
        return markup

    @staticmethod
    def remove_keyboard() -> types.ReplyKeyboardRemove:
        return types.ReplyKeyboardRemove()

    def rules_keyboard(self) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Общие правила", callback_data="rules_common"),
            types.InlineKeyboardButton("Правила RP", callback_data="rules_rp"),
            types.InlineKeyboardButton("Правила чата", callback_data="rules_chat"),
            types.InlineKeyboardButton("Система наказаний", callback_data="rules_punish"),
        )
        return markup

    def faq_keyboard(self) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Как зайти на сервер?", callback_data="faq_join"),
            types.InlineKeyboardButton("Не заходит в игру / ошибка", callback_data="faq_crash"),
            types.InlineKeyboardButton("Как получить разбан?", callback_data="faq_unban"),
            types.InlineKeyboardButton("Где скачать сборку?", callback_data="faq_mods"),
            types.InlineKeyboardButton("Потерял прогресс / вещи", callback_data="faq_progress"),
        )
        return markup

    # ── Обработчики ──
    def handle_start(self, message: types.Message):
        self.user_states[message.chat.id] = None
        self.bot.send_message(
            message.chat.id,
            f"⚡️ Добро пожаловать в бот поддержки сервера <b>{config.SERVER_NAME}</b>!\n"
            "Чем я могу помочь? Выберите раздел ниже:",
            reply_markup=self.main_keyboard()
        )

    def show_rules(self, message: types.Message):
        self.bot.send_message(message.chat.id, "📋 Выберите раздел правил:", reply_markup=self.rules_keyboard())

    def show_ip(self, message: types.Message):
        self.bot.send_message(
            message.chat.id,
            f"🌍 <b>IP адрес сервера:</b> <code>{config.SERVER_IP}</code>\n\n"
            "Для подключения используйте наш лаунчер.\n"
            "Лаунчер можно скачать с нашего телеграм канала."
        )

    def start_complaint(self, message: types.Message):
        self.user_states[message.chat.id] = UserState.MAKING_COMPLAINT
        self.bot.send_message(
            message.chat.id,
            "📝 <b>Подача жалобы на игрока</b>\n\n"
            "Опишите ситуацию: ник нарушителя, что произошло, когда, приложите доказательства.\n"
            "Отправьте всё одним сообщением.\n"
            "Для отмены нажмите /start.",
            reply_markup=self.remove_keyboard()
        )

    def show_faq(self, message: types.Message):
        self.bot.send_message(message.chat.id, "🆘 Часто задаваемые вопросы:", reply_markup=self.faq_keyboard())

    def contact_admin(self, message: types.Message):
        self.user_states[message.chat.id] = UserState.WAITING_FOR_ADMIN
        self.bot.send_message(
            message.chat.id,
            "📞 Вы перешли в режим связи с администрацией.\n"
            "Опишите ваш вопрос, и мы ответим в ближайшее время.\n"
            "Для выхода нажмите /start.",
            reply_markup=self.remove_keyboard()
        )

    def process_complaint(self, message: types.Message):
        self.user_states[message.chat.id] = None
        complaint_id = f"ЖАЛОБА-{message.date.strftime('%Y%m%d%H%M%S')}"
        admin_text = (
            f"📨 <b>Новая жалоба</b>\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"ID пользователя: <code>{message.chat.id}</code>\n"
            f"Номер: <b>{complaint_id}</b>\n\n"
            f"{message.text}"
        )
        if self.admin_chat_id:
            self.bot.send_message(self.admin_chat_id, admin_text)
        self.bot.send_message(
            message.chat.id,
            f"✅ Ваша жалоба принята (№ {complaint_id}). Администрация рассмотрит её в ближайшее время.",
            reply_markup=self.main_keyboard()
        )

    def forward_to_admin(self, message: types.Message):
        forward_text = (
            f"📩 <b>Сообщение от пользователя</b>\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"ID: <code>{message.chat.id}</code>\n\n"
            f"{message.text}"
        )
        if self.admin_chat_id:
            self.bot.send_message(self.admin_chat_id, forward_text)
        self.bot.send_message(message.chat.id, "✅ Ваше сообщение отправлено администрации. Ожидайте ответа.")

    def admin_reply(self, message: types.Message):
        """Ответ администратора пользователю (только из админского чата)."""
        if str(message.chat.id) != self.admin_chat_id:
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            self.bot.send_message(message.chat.id, "Использование: /reply <user_id> <текст>")
            return
        user_id = parts[1]
        reply_text = parts[2]
        try:
            self.bot.send_message(int(user_id), f"💬 <b>Ответ от администрации {config.SERVER_NAME}:</b>\n{reply_text}")
            self.bot.send_message(message.chat.id, f"✅ Ответ отправлен пользователю {user_id}")
        except Exception as e:
            self.bot.send_message(message.chat.id, f"❌ Ошибка при отправке: {e}")

    def handle_rules_callback(self, call: types.CallbackQuery):
        key = call.data.replace("rules_", "")
        text = RULES.get(key, "Раздел не найден.")
        self.bot.answer_callback_query(call.id)
        self.bot.send_message(call.message.chat.id, text)

    def handle_faq_callback(self, call: types.CallbackQuery):
        key = call.data.replace("faq_", "")
        text = FAQ.get(key, "Ответ не найден.")
        self.bot.answer_callback_query(call.id)
        self.bot.send_message(call.message.chat.id, text)

    def fallback(self, message: types.Message):
        self.bot.send_message(message.chat.id, "Используйте кнопки меню или /start для возврата.")

# ─────────────────────────── Flask приложение ───────────────────────────
def create_app(bot_instance: SupportBot) -> Flask:
    app = Flask(__name__)

    @app.route(f"/{config.BOT_TOKEN}", methods=['POST'])
    def webhook():
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot_instance.bot.process_new_updates([update])
            return ''
        else:
            abort(403)

    @app.route('/')
    def index():
        return f"{config.SERVER_NAME} support bot is running."

    return app

# ─────────────────────────── Точка входа ───────────────────────────
def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    support_bot = SupportBot(config.BOT_TOKEN, config.ADMIN_CHAT_ID)

    if config.WEBHOOK_URL:
        # Настройка вебхука и запуск Flask
        support_bot.bot.remove_webhook()
        support_bot.bot.set_webhook(url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}")
        logging.info(f"Webhook установлен на {config.WEBHOOK_URL}/{config.BOT_TOKEN}")

        app = create_app(support_bot)
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        # Polling для локальной разработки
        support_bot.bot.remove_webhook()
        logging.info("Запуск в режиме polling...")
        support_bot.bot.infinity_polling()

if __name__ == "__main__":
    main()
