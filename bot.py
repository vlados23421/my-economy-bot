import os
import logging
import json
import random
import string
from threading import Thread
from datetime import datetime
from flask import Flask, request, abort, render_template
import telebot
from telebot import types

# ─────────────────────────── ПЕРЕМЕННЫЕ ───────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# База данных
players = {}
promocodes = {}
server_news = "🦑 Новый сезон Squid Game! Играйте и выигрывайте!"
bot_started = datetime.now().strftime("%d.%m.%Y %H:%M")

# ─────────────────────────── ПРОВЕРКА АДМИНА ───────────────────────────
def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_CHAT_ID

# ─────────────────────────── КЛАВИАТУРЫ ───────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🦑 Играть", "💰 Баланс")
    markup.add("🏆 Рейтинг", "🎁 Промокод")
    markup.add("📰 Новости", "📢 Пригласить")
    markup.add("ℹ️ Правила")
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🦑 Играть", "💰 Баланс")
    markup.add("🏆 Рейтинг", "🎁 Промокод")
    markup.add("📰 Новости", "📢 Пригласить")
    markup.add("🔧 Админ-панель", "ℹ️ Правила")
    return markup

def admin_panel_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_create_promo"),
        types.InlineKeyboardButton("📋 Список промокодов", callback_data="admin_list_promo"),
        types.InlineKeyboardButton("📰 Изменить новость", callback_data="admin_set_news"),
        types.InlineKeyboardButton("💰 Выдать валюту", callback_data="admin_give_coins"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("👤 Инфо об игроке", callback_data="admin_player_info"),
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
    )
    return markup

def webapp_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "🦑 ИГРАТЬ В SQUID GAME",
        web_app=types.WebAppInfo(url="https://my-economy-bot.onrender.com/game")
    ))
    return markup

# ─────────────────────────── ОБРАБОТЧИКИ КОМАНД ───────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    
    # Проверка реферала
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        ref_id = args[1][3:]
        if ref_id != user_id[-4:]:
            if user_id not in players:
                players[user_id] = {"name": message.from_user.first_name, "username": message.from_user.username or "Игрок", "balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0}
            players[user_id]['balance'] += 50
            bot.send_message(message.chat.id, "🎁 Вы получили +50 монет за регистрацию по реферальной ссылке!")
    
    if user_id not in players:
        players[user_id] = {
            "name": message.from_user.first_name,
            "username": message.from_user.username or "Игрок",
            "balance": 100,
            "games_played": 0,
            "high_score": 0,
            "wins": 0,
            "losses": 0,
            "join_date": datetime.now().strftime("%d.%m.%Y"),
        }
    
    text = (
        "🦑 <b>SQUID GAME</b>\n\n"
        f"Добро пожаловать, Игрок #{user_id[-4:]}!\n"
        f"💰 Стартовый бонус: <b>100 монет</b>\n\n"
        "🎮 <b>Игры:</b> Красный свет, Соты, Кости, Угадай число\n"
        "🏆 Зарабатывай монеты и стань №1 в рейтинге!"
    )
    
    kb = admin_keyboard() if is_admin(message.chat.id) else main_keyboard()
    bot.send_message(message.chat.id, text, reply_markup=kb)

# ── Игры ──
@bot.message_handler(func=lambda m: m.text == "🦑 Играть")
def play_game(message):
    bot.send_message(message.chat.id, "🦑 Нажмите кнопку ниже, чтобы открыть игры:", reply_markup=webapp_keyboard())

# ── Баланс ──
@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(message):
    user_id = str(message.chat.id)
    p = players.get(user_id, {"balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0})
    text = (
        "💰 <b>ВАШ СЧЁТ</b>\n\n"
        f"👤 <b>{p.get('name', 'Игрок')}</b>\n"
        f"💎 Баланс: <b>{p['balance']} монет</b>\n"
        f"🎮 Игр: <b>{p['games_played']}</b>\n"
        f"🏆 Побед: <b>{p['wins']}</b> | 💀 Поражений: <b>{p['losses']}</b>\n"
        f"⭐ Рекорд: <b>{p['high_score']}</b>"
    )
    bot.send_message(message.chat.id, text)

# ── Рейтинг ──
@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    if not players:
        bot.send_message(message.chat.id, "🏆 Пока нет игроков.")
        return
    sorted_players = sorted(players.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["👤"] * 7
    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
    for i, (uid, p) in enumerate(sorted_players):
        name = p.get('name', f"Игрок {uid[-4:]}")
        text += f"{medals[i]} <b>{name}</b> — {p['balance']} монет\n"
    bot.send_message(message.chat.id, text)

# ── Промокод ──
@bot.message_handler(func=lambda m: m.text == "🎁 Промокод")
def promo_info(message):
    text = "🎁 <b>ПРОМОКОДЫ</b>\n\nВведите промокод для получения бонуса!\n\nДоступные промокоды можно найти в новостях или получить от друзей."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 Ввести промокод", callback_data="enter_promo"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📰 Новости")
def news(message):
    bot.send_message(message.chat.id, f"📰 <b>НОВОСТИ</b>\n\n{server_news}")

@bot.message_handler(func=lambda m: m.text == "📢 Пригласить")
def invite(message):
    user_id = str(message.chat.id)
    bot_username = bot.get_me().username
    text = (
        "📢 <b>ПРИГЛАСИ ДРУГА!</b>\n\n"
        f"Отправь ссылку:\n<code>https://t.me/{bot_username}?start=ref{user_id[-4:]}</code>\n\n"
        "За друга: <b>+50 монет</b> вам и другу!"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Правила")
def rules(message):
    text = (
        "🦑 <b>ПРАВИЛА</b>\n\n"
        "🟢 <b>Красный свет — Зелёный свет:</b> Беги на зелёный, замри на красный!\n"
        "🍬 <b>Соты:</b> Вырезай фигуру, не сломав.\n"
        "🎲 <b>Кости:</b> Чёт/нечет — удвой ставку!\n"
        "🔢 <b>Число:</b> Угадай от 1 до 100 за 7 попыток.\n\n"
        "🎁 Промокоды дают бонусы!\n"
        "📢 Приглашай друзей и получай монеты!"
    )
    bot.send_message(message.chat.id, text)

# ── Админ-панель ──
@bot.message_handler(func=lambda m: m.text == "🔧 Админ-панель" and is_admin(m.chat.id))
def admin_panel(message):
    bot.send_message(message.chat.id, "🔧 <b>АДМИН-ПАНЕЛЬ</b>\nВыберите действие:", reply_markup=admin_panel_keyboard())

# Приём данных из Web App
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    user_id = str(message.chat.id)
    data = json.loads(message.web_app_data.data)
    game = data.get('game', 'Неизвестная игра')
    score = data.get('score', 0)
    reward = data.get('reward', 0)
    
    if user_id not in players:
        players[user_id] = {"name": message.from_user.first_name, "username": message.from_user.username or "Игрок", "balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0}
    
    players[user_id]['balance'] += reward
    players[user_id]['games_played'] += 1
    players[user_id]['high_score'] = max(players[user_id]['high_score'], score)
    if reward > 0: players[user_id]['wins'] += 1
    else: players[user_id]['losses'] += 1
    
    logger.info(f"Игрок {user_id}: {game}, счёт {score}, +{reward} монет, баланс {players[user_id]['balance']}")
    
    result_text = (
        f"🎉 <b>ИГРА ЗАВЕРШЕНА!</b>\n\n"
        f"🎮 {game}\n📊 Очки: <b>{score}</b>\n"
        f"💰 +{reward} монет\n💎 Баланс: <b>{players[user_id]['balance']}</b>"
    )
    bot.send_message(message.chat.id, result_text, reply_markup=webapp_keyboard())

# ─────────────────────────── CALLBACK-ОБРАБОТЧИКИ ───────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == "enter_promo")
def enter_promo(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔑 Введите промокод:", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    code = message.text.strip().upper()
    if code in promocodes:
        promo = promocodes[code]
        if promo['used_by'] and message.chat.id in promo['used_by']:
            bot.send_message(message.chat.id, "❌ Вы уже использовали этот промокод!", reply_markup=admin_keyboard() if is_admin(message.chat.id) else main_keyboard())
            return
        if promo['max_uses'] and len(promo.get('used_by', [])) >= promo['max_uses']:
            bot.send_message(message.chat.id, "❌ Промокод больше не действителен!", reply_markup=admin_keyboard() if is_admin(message.chat.id) else main_keyboard())
            return
        
        user_id = str(message.chat.id)
        if user_id not in players:
            players[user_id] = {"name": message.from_user.first_name, "username": message.from_user.username or "Игрок", "balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0}
        
        players[user_id]['balance'] += promo['reward']
        if 'used_by' not in promo: promo['used_by'] = []
        promo['used_by'].append(message.chat.id)
        
        bot.send_message(message.chat.id, f"🎁 Промокод активирован! +{promo['reward']} монет!\n💰 Баланс: {players[user_id]['balance']}", reply_markup=admin_keyboard() if is_admin(message.chat.id) else main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Промокод не найден!", reply_markup=admin_keyboard() if is_admin(message.chat.id) else main_keyboard())

# Админские callback-и
@bot.callback_query_handler(func=lambda call: call.data == "admin_create_promo" and is_admin(call.from_user.id))
def admin_create_promo(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎁 <b>Создание промокода</b>\n\nВведите в формате:\n<code>КОД | НАГРАДА | МАКС_ИСПОЛЬЗОВАНИЙ</code>\n\nПример: <code>BEST2026 | 500 | 50</code>\n(0 = безлимит)", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_create_promo)

def process_create_promo(message):
    try:
        parts = message.text.split("|")
        code = parts[0].strip().upper()
        reward = int(parts[1].strip())
        max_uses = int(parts[2].strip()) if len(parts) > 2 else 0
        
        promocodes[code] = {"reward": reward, "max_uses": max_uses, "used_by": [], "created_by": message.chat.id, "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")}
        bot.send_message(message.chat.id, f"✅ Промокод <b>{code}</b> создан!\n💰 Награда: {reward} монет\n👥 Использований: {max_uses if max_uses else 'Безлимит'}", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат!", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_promo" and is_admin(call.from_user.id))
def admin_list_promo(call):
    bot.answer_callback_query(call.id)
    if not promocodes:
        bot.send_message(call.message.chat.id, "📋 Нет созданных промокодов.")
        return
    text = "📋 <b>ПРОМОКОДЫ:</b>\n\n"
    for code, p in promocodes.items():
        used = len(p.get('used_by', []))
        max_u = p['max_uses'] if p['max_uses'] else '∞'
        text += f"<b>{code}</b> — {p['reward']} монет | {used}/{max_u} исп.\n"
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_news" and is_admin(call.from_user.id))
def admin_set_news(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📰 Введите текст новости:", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_set_news)

def process_set_news(message):
    global server_news
    server_news = message.text
    bot.send_message(message.chat.id, f"✅ Новость обновлена:\n{server_news}", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_give_coins" and is_admin(call.from_user.id))
def admin_give_coins(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💰 <b>Выдать валюту</b>\n\nВведите:\n<code>ID_игрока | СУММА</code>\n\nID можно найти в /players", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_give_coins)

def process_give_coins(message):
    try:
        parts = message.text.split("|")
        uid = parts[0].strip()
        amount = int(parts[1].strip())
        if uid in players:
            players[uid]['balance'] += amount
            bot.send_message(message.chat.id, f"✅ Игроку {uid} выдано {amount} монет.", reply_markup=admin_keyboard())
            try: bot.send_message(int(uid), f"🎁 Администратор выдал вам <b>{amount} монет</b>!\n💰 Баланс: {players[uid]['balance']}")
            except: pass
        else:
            bot.send_message(message.chat.id, "❌ Игрок не найден!", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат!", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats" and is_admin(call.from_user.id))
def admin_stats(call):
    bot.answer_callback_query(call.id)
    total_players = len(players)
    total_coins = sum(p['balance'] for p in players.values())
    total_games = sum(p['games_played'] for p in players.values())
    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Игроков: <b>{total_players}</b>\n"
        f"💰 Всего монет: <b>{total_coins}</b>\n"
        f"🎮 Всего игр: <b>{total_games}</b>\n"
        f"🎁 Промокодов: <b>{len(promocodes)}</b>\n"
        f"⏰ Запущен: {bot_started}"
    )
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_player_info" and is_admin(call.from_user.id))
def admin_player_info(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👤 Введите ID игрока (4 цифры):", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_player_info)

def process_player_info(message):
    uid = None
    for pid in players:
        if pid.endswith(message.text.strip()):
            uid = pid
            break
    if uid and uid in players:
        p = players[uid]
        text = (
            f"👤 <b>ИГРОК #{uid[-4:]}</b>\n\n"
            f"Имя: <b>{p.get('name', '—')}</b>\n"
            f"Username: @{p.get('username', '—')}\n"
            f"💰 Баланс: <b>{p['balance']}</b>\n"
            f"🎮 Игр: <b>{p['games_played']}</b>\n"
            f"🏆 Побед: <b>{p['wins']}</b> | 💀 Поражений: <b>{p['losses']}</b>\n"
            f"⭐ Рекорд: <b>{p['high_score']}</b>\n"
            f"📅 В боте с: {p.get('join_date', '—')}"
        )
        bot.send_message(message.chat.id, text, reply_markup=admin_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Игрок не найден!", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast" and is_admin(call.from_user.id))
def admin_broadcast(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Введите текст для рассылки всем игрокам:", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    sent = 0
    for uid in players:
        try:
            bot.send_message(int(uid), f"📢 <b>РАССЫЛКА</b>\n\n{message.text}")
            sent += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Рассылка отправлена {sent}/{len(players)} игрокам.", reply_markup=admin_keyboard())

# ── Команда /players (админ) ──
@bot.message_handler(commands=['players'])
def cmd_players(message):
    if not is_admin(message.chat.id): return
    if not players:
        bot.send_message(message.chat.id, "Нет игроков.")
        return
    text = "📋 <b>СПИСОК ИГРОКОВ</b>\n\n"
    for uid, p in list(players.items())[:20]:
        text += f"<code>{uid[-4:]}</code> — {p.get('name', '—')} | {p['balance']} монет\n"
    bot.send_message(message.chat.id, text)

# ── Fallback ──
@bot.message_handler(func=lambda m: True)
def fallback(message):
    kb = admin_keyboard() if is_admin(message.chat.id) else main_keyboard()
    bot.send_message(message.chat.id, "Используйте кнопки меню или /start", reply_markup=kb)

# ─────────────────────────── FLASK ───────────────────────────
@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/')
def index():
    return "Squid Game Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

# ─────────────────────────── ЗАПУСК ───────────────────────────
if __name__ == "__main__":
    logger.info("Запуск Squid Game бота...")
    Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
