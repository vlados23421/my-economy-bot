import os
import logging
import json
import random
from threading import Thread
from datetime import datetime
from flask import Flask, request, abort, render_template, jsonify
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

# Новости для Web App
web_news = [
    {
        "id": 1,
        "tag": "event",
        "tag_text": "🔥 Событие",
        "title": "Турнир недели!",
        "description": "Топ-3 игрока получат VIP и 5000 монет!",
        "date": "До 31 декабря",
        "featured": True
    },
    {
        "id": 2,
        "tag": "promo",
        "tag_text": "🎁 Промокод",
        "title": "SQUID2026",
        "description": "+300 монет для новых игроков!",
        "date": "Активируй сейчас",
        "featured": False
    }
]
news_id_counter = 2

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
        types.InlineKeyboardButton("📰 Создать новость", callback_data="admin_create_news"),
        types.InlineKeyboardButton("📋 Список новостей", callback_data="admin_list_news"),
        types.InlineKeyboardButton("🗑 Удалить новость", callback_data="admin_delete_news"),
        types.InlineKeyboardButton("💰 Выдать валюту", callback_data="admin_give_coins"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
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
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        ref_id = args[1][3:]
        if ref_id != user_id[-4:]:
            if user_id not in players:
                players[user_id] = {"name": message.from_user.first_name, "username": message.from_user.username or "Игрок", "balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0}
            players[user_id]['balance'] += 50
            bot.send_message(message.chat.id, "🎁 Вы получили +50 монет за реферала!")
    
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
        "🎮 Игры: Красный свет, Соты, Кости, Угадай число\n"
        "🏆 Зарабатывай монеты и стань №1!"
    )
    
    kb = admin_keyboard() if is_admin(message.chat.id) else main_keyboard()
    bot.send_message(message.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🦑 Играть")
def play_game(message):
    bot.send_message(message.chat.id, "🦑 Нажмите кнопку ниже:", reply_markup=webapp_keyboard())

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

@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    if not players:
        bot.send_message(message.chat.id, "🏆 Пока нет игроков."); return
    sorted_players = sorted(players.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["👤"] * 7
    text = "🏆 <b>ТОП-10</b>\n\n"
    for i, (uid, p) in enumerate(sorted_players):
        text += f"{medals[i]} <b>{p.get('name', uid[-4:])}</b> — {p['balance']} монет\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🎁 Промокод")
def promo_info(message):
    text = "🎁 Введите промокод для бонуса!"
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
    text = f"📢 Отправь другу:\n<code>https://t.me/{bot_username}?start=ref{user_id[-4:]}</code>\n\n+50 монет вам и другу!"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Правила")
def rules(message):
    text = "🦑 <b>ПРАВИЛА</b>\n\n🟢 Беги на зелёный!\n🍬 Режь соты!\n🎲 Чёт/нечет!\n🔢 Угадай число!"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🔧 Админ-панель" and is_admin(m.chat.id))
def admin_panel(message):
    bot.send_message(message.chat.id, "🔧 <b>АДМИН-ПАНЕЛЬ</b>", reply_markup=admin_panel_keyboard())

# Приём данных из Web App
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    user_id = str(message.chat.id)
    data = json.loads(message.web_app_data.data)
    game = data.get('game', 'Игра')
    score = data.get('score', 0)
    reward = data.get('reward', 0)
    
    if user_id not in players:
        players[user_id] = {"name": message.from_user.first_name, "username": message.from_user.username or "Игрок", "balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0}
    
    players[user_id]['balance'] += reward
    players[user_id]['games_played'] += 1
    players[user_id]['high_score'] = max(players[user_id]['high_score'], score)
    if reward > 0: players[user_id]['wins'] += 1
    else: players[user_id]['losses'] += 1
    
    result_text = f"🎉 <b>ИГРА ЗАВЕРШЕНА!</b>\n\n🎮 {game}\n📊 Очки: <b>{score}</b>\n💰 +{reward} монет\n💎 Баланс: <b>{players[user_id]['balance']}</b>"
    bot.send_message(message.chat.id, result_text, reply_markup=webapp_keyboard())

# ─────────────────────────── CALLBACK-ОБРАБОТЧИКИ ───────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == "enter_promo")
def enter_promo(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔑 Введите промокод:", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    code = message.text.strip().upper()
    kb = admin_keyboard() if is_admin(message.chat.id) else main_keyboard()
    if code in promocodes:
        promo = promocodes[code]
        if message.chat.id in promo.get('used_by', []):
            bot.send_message(message.chat.id, "❌ Вы уже использовали этот промокод!", reply_markup=kb); return
        if promo['max_uses'] and len(promo.get('used_by', [])) >= promo['max_uses']:
            bot.send_message(message.chat.id, "❌ Промокод закончился!", reply_markup=kb); return
        user_id = str(message.chat.id)
        if user_id not in players:
            players[user_id] = {"name": message.from_user.first_name, "username": message.from_user.username or "Игрок", "balance": 0, "games_played": 0, "high_score": 0, "wins": 0, "losses": 0}
        players[user_id]['balance'] += promo['reward']
        if 'used_by' not in promo: promo['used_by'] = []
        promo['used_by'].append(message.chat.id)
        bot.send_message(message.chat.id, f"🎁 +{promo['reward']} монет!\n💰 Баланс: {players[user_id]['balance']}", reply_markup=kb)
    else:
        bot.send_message(message.chat.id, "❌ Не найден!", reply_markup=kb)

# Админ: создать промокод
@bot.callback_query_handler(func=lambda call: call.data == "admin_create_promo" and is_admin(call.from_user.id))
def admin_create_promo(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎁 Формат:\n<code>КОД | НАГРАДА | МАКС_ИСП</code>\nПример: <code>SQUID | 500 | 50</code>", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_create_promo)

def process_create_promo(message):
    try:
        parts = message.text.split("|")
        code = parts[0].strip().upper()
        reward = int(parts[1].strip())
        max_uses = int(parts[2].strip()) if len(parts) > 2 else 0
        promocodes[code] = {"reward": reward, "max_uses": max_uses, "used_by": [], "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")}
        bot.send_message(message.chat.id, f"✅ Промокод <b>{code}</b> создан! (+{reward} монет)", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат!", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_promo" and is_admin(call.from_user.id))
def admin_list_promo(call):
    bot.answer_callback_query(call.id)
    if not promocodes:
        bot.send_message(call.message.chat.id, "📋 Нет промокодов."); return
    text = "📋 <b>ПРОМОКОДЫ:</b>\n\n"
    for code, p in promocodes.items():
        used = len(p.get('used_by', []))
        max_u = p['max_uses'] if p['max_uses'] else '∞'
        text += f"<b>{code}</b> — {p['reward']} монет | {used}/{max_u}\n"
    bot.send_message(call.message.chat.id, text)

# Админ: создать новость
@bot.callback_query_handler(func=lambda call: call.data == "admin_create_news" and is_admin(call.from_user.id))
def admin_create_news(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📰 <b>Создание новости</b>\n\nФормат:\n<code>ТЕГ | ЗАГОЛОВОК | ОПИСАНИЕ | ДАТА | FEATURED</code>\n\nТеги: event, promo, update, hot\nFeatured: yes/no\n\nПример:\n<code>promo | NEW2026 | +500 монет! | До 31.12 | yes</code>", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_create_news)

def process_create_news(message):
    global news_id_counter
    try:
        parts = message.text.split("|")
        tag = parts[0].strip()
        title = parts[1].strip()
        desc = parts[2].strip()
        date = parts[3].strip() if len(parts) > 3 else ""
        featured = parts[4].strip().lower() == "yes" if len(parts) > 4 else False
        
        tag_map = {
            "event": ("🔥 Событие", "tag-event"),
            "promo": ("🎁 Промокод", "tag-promo"),
            "update": ("🔄 Обновление", "tag-update"),
            "hot": ("🔴 Хит", "tag-hot"),
        }
        tag_text, tag_class = tag_map.get(tag, ("📌 Новость", "tag-event"))
        
        news_id_counter += 1
        web_news.insert(0, {
            "id": news_id_counter,
            "tag": tag_class,
            "tag_text": tag_text,
            "title": title,
            "description": desc,
            "date": date,
            "featured": featured
        })
        
        bot.send_message(message.chat.id, f"✅ Новость создана!\n<b>{title}</b>", reply_markup=admin_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: ТЕГ | ЗАГОЛОВОК | ОПИСАНИЕ | ДАТА | FEATURED", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_news" and is_admin(call.from_user.id))
def admin_list_news(call):
    bot.answer_callback_query(call.id)
    if not web_news:
        bot.send_message(call.message.chat.id, "📋 Нет новостей."); return
    text = "📋 <b>НОВОСТИ В WEB APP:</b>\n\n"
    for n in web_news:
        f = "⭐ " if n['featured'] else ""
        text += f"{f}<b>#{n['id']}</b> {n['title']} — {n['tag_text']}\n"
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_news" and is_admin(call.from_user.id))
def admin_delete_news(call):
    bot.answer_callback_query(call.id)
    if not web_news:
        bot.send_message(call.message.chat.id, "Нет новостей для удаления."); return
    markup = types.InlineKeyboardMarkup()
    for n in web_news[:10]:
        markup.add(types.InlineKeyboardButton(f"#{n['id']} {n['title']}", callback_data=f"delnews_{n['id']}"))
    bot.send_message(call.message.chat.id, "Выберите новость для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delnews_"))
def delete_news_by_id(call):
    if not is_admin(call.from_user.id): return
    nid = int(call.data.replace("delnews_", ""))
    global web_news
    web_news = [n for n in web_news if n['id'] != nid]
    bot.answer_callback_query(call.id, "✅ Новость удалена!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_give_coins" and is_admin(call.from_user.id))
def admin_give_coins(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💰 Формат: <code>ID | СУММА</code>", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_give_coins)

def process_give_coins(message):
    try:
        parts = message.text.split("|")
        uid, amount = parts[0].strip(), int(parts[1].strip())
        if uid in players:
            players[uid]['balance'] += amount
            bot.send_message(message.chat.id, f"✅ Игроку {uid} +{amount} монет.", reply_markup=admin_keyboard())
            try: bot.send_message(int(uid), f"🎁 Админ выдал +{amount} монет!\n💰 Баланс: {players[uid]['balance']}")
            except: pass
        else:
            bot.send_message(message.chat.id, "❌ Не найден!", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат!", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats" and is_admin(call.from_user.id))
def admin_stats(call):
    bot.answer_callback_query(call.id)
    text = (
        "📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Игроков: <b>{len(players)}</b>\n"
        f"💰 Монет: <b>{sum(p['balance'] for p in players.values())}</b>\n"
        f"🎮 Игр: <b>{sum(p['games_played'] for p in players.values())}</b>\n"
        f"🎁 Промокодов: <b>{len(promocodes)}</b>\n"
        f"📰 Новостей: <b>{len(web_news)}</b>\n"
        f"⏰ Запущен: {bot_started}"
    )
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast" and is_admin(call.from_user.id))
def admin_broadcast(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Текст рассылки:", reply_markup=remove_kb())
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    sent = 0
    for uid in players:
        try:
            bot.send_message(int(uid), f"📢 <b>РАССЫЛКА</b>\n\n{message.text}")
            sent += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Отправлено {sent}/{len(players)}", reply_markup=admin_keyboard())

# ─────────────────────────── FLASK API ───────────────────────────
@app.route('/api/news')
def api_news():
    """API для получения новостей в Web App"""
    return jsonify(web_news)

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
    logger.info("Запуск Squid Game бота с API...")
    Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
