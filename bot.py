import os
import logging
import random
import datetime
from typing import Dict, List, Optional

import telebot
from telebot import types
from flask import Flask, request, abort

# ─────────────────────────── ПЕРЕМЕННЫЕ ───────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

SERVER_NAME = "BEST RUSSIA"
SERVER_IP = "185.169.134.5:7777"

# ─────────────────────────── ЛОГГЕР ───────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────── БОТ ───────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_states: Dict[int, Optional[str]] = {}

# Хранилище розыгрышей
giveaways: Dict[str, dict] = {}
giveaway_counter = 0

# ─────────────────────────── КЛАВИАТУРЫ ───────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎉 Активные розыгрыши", "🎫 Мои участия")
    markup.add("🏆 История побед", "📊 Статистика")
    markup.add("ℹ️ Как играть", "🎁 Призы")
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎉 Активные розыгрыши", "🎫 Мои участия")
    markup.add("➕ Создать розыгрыш", "❌ Удалить розыгрыш")
    markup.add("🎯 Выбрать победителя", "📋 Все розыгрыши")
    markup.add("🔙 Обычное меню")
    return markup

def remove_kb():
    return types.ReplyKeyboardRemove()

# ─────────────────────────── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ───────────────────────────
def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором."""
    return str(user_id) == ADMIN_CHAT_ID

def get_active_giveaways() -> List[tuple]:
    """Получить список активных розыгрышей."""
    return [(gid, g) for gid, g in giveaways.items() if g["status"] == "active"]

def get_user_giveaways(user_id: int) -> List[tuple]:
    """Получить розыгрыши, в которых участвует пользователь."""
    result = []
    for gid, g in giveaways.items():
        if user_id in g["participants"]:
            result.append((gid, g))
    return result

# ─────────────────────────── ОБРАБОТЧИКИ ───────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_states[message.chat.id] = None
    
    welcome_text = (
        f"🎉 <b>Добро пожаловать в бот розыгрышей {SERVER_NAME}!</b>\n\n"
        "Здесь вы можете участвовать в розыгрышах и выигрывать крутые призы:\n"
        "💰 Игровая валюта\n"
        "💎 VIP-статус\n"
        "🚗 Уникальные авто\n"
        "🎁 И многое другое!\n\n"
        "Выберите действие в меню:"
    )
    
    if is_admin(message.chat.id):
        bot.send_message(message.chat.id, welcome_text + "\n\n🔧 <i>У вас права администратора</i>", reply_markup=admin_keyboard())
    else:
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard())

# ── Активные розыгрыши ──
@bot.message_handler(func=lambda m: m.text in ["🎉 Активные розыгрыши", "📋 Все розыгрыши"])
def show_active_giveaways(message):
    active = get_active_giveaways()
    all_giveaways = [(gid, g) for gid, g in giveaways.items()]
    
    if not all_giveaways:
        bot.send_message(message.chat.id, "😔 Сейчас нет активных розыгрышей. Заходите позже!")
        return
    
    for gid, g in giveaways.items():
        status = "🟢 Активен" if g["status"] == "active" else "🔴 Завершён"
        winner_text = f"\n🏆 Победитель: @{g.get('winner_name', 'Не определён')}" if g.get("winner_name") else ""
        
        text = (
            f"<b>🎁 Розыгрыш #{gid}</b>\n"
            f"📛 Статус: {status}\n"
            f"🎯 Приз: <b>{g['prize']}</b>\n"
            f"👥 Участников: <b>{len(g['participants'])}</b>\n"
            f"📅 Создан: {g['created']}\n"
            f"⏰ Завершение: {g['end_time']}{winner_text}"
        )
        
        markup = types.InlineKeyboardMarkup()
        if g["status"] == "active" and message.chat.id not in g["participants"]:
            markup.add(types.InlineKeyboardButton("🎫 Участвовать!", callback_data=f"join_{gid}"))
        elif g["status"] == "active" and message.chat.id in g["participants"]:
            markup.add(types.InlineKeyboardButton("✅ Вы участвуете", callback_data="none"))
        
        if is_admin(message.chat.id) and g["status"] == "active":
            markup.add(types.InlineKeyboardButton("🎯 Выбрать победителя", callback_data=f"draw_{gid}"))
            markup.add(types.InlineKeyboardButton("❌ Удалить", callback_data=f"delete_{gid}"))
        
        bot.send_message(message.chat.id, text, reply_markup=markup)

# ── Мои участия ──
@bot.message_handler(func=lambda m: m.text == "🎫 Мои участия")
def my_participations(message):
    my_giveaways = get_user_giveaways(message.chat.id)
    
    if not my_giveaways:
        bot.send_message(message.chat.id, "😔 Вы пока не участвуете ни в одном розыгрыше.")
        return
    
    text = "🎫 <b>Ваши участия в розыгрышах:</b>\n\n"
    for gid, g in my_giveaways:
        status = "🟢 Активен" if g["status"] == "active" else "🔴 Завершён"
        won = " 🏆 ПОБЕДА!" if g.get("winner_id") == message.chat.id else ""
        text += f"<b>#{gid}</b> | {g['prize']} | {status}{won}\n"
    
    bot.send_message(message.chat.id, text)

# ── История побед ──
@bot.message_handler(func=lambda m: m.text == "🏆 История побед")
def winners_history(message):
    won_giveaways = [(gid, g) for gid, g in giveaways.items() if g.get("winner_id") == message.chat.id]
    
    if not won_giveaways:
        bot.send_message(message.chat.id, "🏆 Пока нет побед. Участвуйте в розыгрышах и выигрывайте!")
        return
    
    text = "🏆 <b>Ваши победы:</b>\n\n"
    for gid, g in won_giveaways:
        text += f"🎁 <b>#{gid}</b> — {g['prize']}\n📅 {g['end_time']}\n\n"
    
    bot.send_message(message.chat.id, text)

# ── Статистика ──
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def statistics(message):
    total_giveaways = len(giveaways)
    active_count = len(get_active_giveaways())
    completed_count = total_giveaways - active_count
    
    all_participants = set()
    for g in giveaways.values():
        all_participants.update(g["participants"])
    
    text = (
        "📊 <b>Статистика розыгрышей</b>\n\n"
        f"🎁 Всего розыгрышей: <b>{total_giveaways}</b>\n"
        f"🟢 Активных: <b>{active_count}</b>\n"
        f"🔴 Завершённых: <b>{completed_count}</b>\n"
        f"👥 Всего участников: <b>{len(all_participants)}</b>\n"
    )
    
    bot.send_message(message.chat.id, text)

# ── Как играть ──
@bot.message_handler(func=lambda m: m.text == "ℹ️ Как играть")
def how_to_play(message):
    text = (
        "ℹ️ <b>Как участвовать в розыгрышах?</b>\n\n"
        "1️⃣ Нажмите <b>«Активные розыгрыши»</b>\n"
        "2️⃣ Выберите интересный розыгрыш\n"
        "3️⃣ Нажмите <b>«Участвовать»</b>\n"
        "4️⃣ Ожидайте результатов!\n\n"
        "🎯 Победитель выбирается случайно среди всех участников.\n"
        "🎁 Призы выдаются администрацией сервера.\n\n"
        "⚠️ <b>Правила:</b>\n"
        "• Один аккаунт — одно участие\n"
        "• Попытки обмана — дисквалификация\n"
        "• Призы необходимо забрать в течение 7 дней"
    )
    bot.send_message(message.chat.id, text)

# ── Призы ──
@bot.message_handler(func=lambda m: m.text == "🎁 Призы")
def prizes_info(message):
    text = (
        "🎁 <b>Возможные призы:</b>\n\n"
        "💰 <b>Игровая валюта:</b>\n"
        "• 10.000$ — 100.000$\n\n"
        "💎 <b>VIP-статус:</b>\n"
        "• VIP на 3 дня\n"
        "• Premium на 7 дней\n"
        "• Gold на 14 дней\n\n"
        "🚗 <b>Транспорт:</b>\n"
        "• Уникальные авто\n"
        "• Мотоциклы\n"
        "• Вертолёты\n\n"
        "🎁 <b>Особые призы:</b>\n"
        "• Скины\n"
        "• Дома\n"
        "• Бизнесы\n\n"
        "Следите за новыми розыгрышами!"
    )
    bot.send_message(message.chat.id, text)

# ── Создать розыгрыш (админ) ──
@bot.message_handler(func=lambda m: m.text == "➕ Создать розыгрыш" and is_admin(m.chat.id))
def create_giveaway_start(message):
    user_states[message.chat.id] = 'creating_giveaway'
    bot.send_message(
        message.chat.id,
        "➕ <b>Создание нового розыгрыша</b>\n\n"
        "Отправьте описание в формате:\n"
        "<code>Приз | Дата завершения</code>\n\n"
        "Пример:\n"
        "<code>50.000$ и VIP на 3 дня | 30.12.2026 18:00</code>\n\n"
        "Для отмены нажмите /start",
        reply_markup=remove_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'creating_giveaway')
def create_giveaway_finish(message):
    global giveaway_counter
    user_states[message.chat.id] = None
    
    try:
        parts = message.text.split("|")
        prize = parts[0].strip()
        end_time = parts[1].strip()
    except:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат! Используйте:\n<code>Приз | Дата завершения</code>",
            reply_markup=admin_keyboard()
        )
        return
    
    giveaway_counter += 1
    gid = f"GIVEAWAY-{giveaway_counter:04d}"
    
    giveaways[gid] = {
        "prize": prize,
        "end_time": end_time,
        "created": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "active",
        "participants": [],
        "winner_id": None,
        "winner_name": None,
        "creator_id": message.chat.id,
    }
    
    bot.send_message(
        message.chat.id,
        f"✅ Розыгрыш создан!\n"
        f"🎁 <b>#{gid}</b> — {prize}\n"
        f"⏰ Завершение: {end_time}",
        reply_markup=admin_keyboard()
    )
    
    # Оповещение всем о новом розыгрыше (если есть канал)
    logger.info(f"Создан новый розыгрыш: {gid}")

# ── Удалить розыгрыш (админ) ──
@bot.message_handler(func=lambda m: m.text == "❌ Удалить розыгрыш" and is_admin(m.chat.id))
def delete_giveaway_start(message):
    active = get_active_giveaways()
    if not active:
        bot.send_message(message.chat.id, "Нет активных розыгрышей для удаления.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for gid, g in active:
        markup.add(types.InlineKeyboardButton(f"#{gid} — {g['prize']}", callback_data=f"delete_{gid}"))
    
    bot.send_message(message.chat.id, "Выберите розыгрыш для удаления:", reply_markup=markup)

# ── Выбрать победителя (админ) ──
@bot.message_handler(func=lambda m: m.text == "🎯 Выбрать победителя" and is_admin(m.chat.id))
def draw_winner_start(message):
    active = get_active_giveaways()
    if not active:
        bot.send_message(message.chat.id, "Нет активных розыгрышей.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for gid, g in active:
        if g["participants"]:
            markup.add(types.InlineKeyboardButton(f"#{gid} — {len(g['participants'])} уч.", callback_data=f"draw_{gid}"))
    
    if not markup.keyboard:
        bot.send_message(message.chat.id, "В активных розыгрышах нет участников.")
        return
    
    bot.send_message(message.chat.id, "Выберите розыгрыш для выбора победителя:", reply_markup=markup)

# ── Обычное меню (админ) ──
@bot.message_handler(func=lambda m: m.text == "🔙 Обычное меню" and is_admin(m.chat.id))
def switch_to_normal(message):
    bot.send_message(message.chat.id, "Переключено на обычное меню.", reply_markup=main_keyboard())

# ─────────────────────────── CALLBACK ОБРАБОТЧИКИ ───────────────────────────
@bot.callback_query_handler(func=lambda call: call.data.startswith("join_"))
def join_giveaway(call):
    gid = call.data.replace("join_", "")
    
    if gid not in giveaways:
        bot.answer_callback_query(call.id, "Розыгрыш не найден!")
        return
    
    g = giveaways[gid]
    
    if g["status"] != "active":
        bot.answer_callback_query(call.id, "Розыгрыш уже завершён!")
        return
    
    if call.from_user.id in g["participants"]:
        bot.answer_callback_query(call.id, "Вы уже участвуете!")
        return
    
    g["participants"].append(call.from_user.id)
    bot.answer_callback_query(call.id, "✅ Вы участвуете! Удачи!")
    
    # Обновляем сообщение
    new_text = call.message.text.replace(
        f"👥 Участников: <b>{len(g['participants']) - 1}</b>",
        f"👥 Участников: <b>{len(g['participants'])}</b>"
    )
    bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("draw_"))
def draw_winner(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Только для администраторов!")
        return
    
    gid = call.data.replace("draw_", "")
    g = giveaways.get(gid)
    
    if not g or g["status"] != "active":
        bot.answer_callback_query(call.id, "Розыгрыш неактивен!")
        return
    
    if not g["participants"]:
        bot.answer_callback_query(call.id, "Нет участников!")
        return
    
    # Выбираем победителя
    winner_id = random.choice(g["participants"])
    g["winner_id"] = winner_id
    g["status"] = "completed"
    
    try:
        winner = bot.get_chat(winner_id)
        g["winner_name"] = winner.username or winner.first_name
    except:
        g["winner_name"] = str(winner_id)
    
    bot.answer_callback_query(call.id, f"Победитель: @{g['winner_name']}!")
    
    # Обновляем сообщение
    winner_text = (
        f"{call.message.text}\n\n"
        f"🎉 <b>ПОБЕДИТЕЛЬ:</b> @{g['winner_name']}\n"
        f"🎁 Приз: <b>{g['prize']}</b>"
    )
    bot.edit_message_text(winner_text, call.message.chat.id, call.message.message_id)
    
    # Оповещаем победителя
    try:
        bot.send_message(
            winner_id,
            f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
            f"Вы выиграли в розыгрыше <b>#{gid}</b>!\n"
            f"🎁 Ваш приз: <b>{g['prize']}</b>\n\n"
            f"Свяжитесь с администрацией для получения приза."
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_giveaway(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Только для администраторов!")
        return
    
    gid = call.data.replace("delete_", "")
    
    if gid in giveaways:
        del giveaways[gid]
        bot.answer_callback_query(call.id, "Розыгрыш удалён!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Розыгрыш не найден!")

@bot.callback_query_handler(func=lambda call: call.data == "none")
def none_callback(call):
    bot.answer_callback_query(call.id)

# ── Fallback ──
@bot.message_handler(func=lambda m: True)
def fallback(message):
    if is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Используйте кнопки меню или /start", reply_markup=admin_keyboard())
    else:
        bot.send_message(message.chat.id, "Используйте кнопки меню или /start", reply_markup=main_keyboard())

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
    return f"{SERVER_NAME} giveaway bot is running."

# ─────────────────────────── ЗАПУСК ───────────────────────────
if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
        logger.info(f"Webhook: {WEBHOOK_URL}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        bot.remove_webhook()
        logger.info("Polling mode...")
        bot.infinity_polling()
