import os
import logging
import json
import random
from threading import Thread
from datetime import datetime, timedelta
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
user_states = {}
server_news = "🦑 Новый сезон Squid Game! Играйте и выигрывайте!"
bot_started = datetime.now().strftime("%d.%m.%Y %H:%M")

# Для банка
deposits = {}

# Новости для сайта
web_news = [
    {"id": 1, "tag": "tag-event", "tag_text": "🔥 Событие", "title": "Турнир недели!", "description": "Топ-3 получат VIP и 5000 монет!", "date": "До 31 декабря", "featured": True},
    {"id": 2, "tag": "tag-promo", "tag_text": "🎁 Промокод", "title": "SQUID1", "description": "+500 монет! 5 использований!", "date": "Активируй сейчас", "featured": False}
]
news_id_counter = 2

# ─────────────────────────── ПРОВЕРКА АДМИНА ───────────────────────────
def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_CHAT_ID

# ─────────────────────────── КЛАВИАТУРЫ ───────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 Игры", "💰 Баланс")
    markup.add("🏆 Рейтинг", "🎁 Промокод")
    markup.add("🏦 Банк", "🎰 Рулетка")
    markup.add("💸 Перевод", "📊 Статистика")
    markup.add("📰 Новости", "ℹ️ Помощь")
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 Игры", "💰 Баланс")
    markup.add("🏆 Рейтинг", "🎁 Промокод")
    markup.add("🏦 Банк", "🎰 Рулетка")
    markup.add("💸 Перевод", "📊 Статистика")
    markup.add("📰 Новости", "🔧 Админ")
    return markup

def games_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🟢 Красный свет — Зелёный свет", callback_data="game_rlgl"),
        types.InlineKeyboardButton("🍬 Сахарные соты", callback_data="game_honeycomb"),
        types.InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
        types.InlineKeyboardButton("🔢 Угадай число", callback_data="game_guess"),
    )
    return markup

def admin_panel_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_create_promo"),
        types.InlineKeyboardButton("📋 Список промокодов", callback_data="admin_list_promo"),
        types.InlineKeyboardButton("📰 Создать новость", callback_data="admin_create_news"),
        types.InlineKeyboardButton("💰 Выдать валюту", callback_data="admin_give_coins"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
    )
    return markup

def remove_kb():
    return types.ReplyKeyboardRemove()

# ─────────────────────────── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ───────────────────────────
def get_player(user_id: str) -> dict:
    if user_id not in players:
        players[user_id] = {
            "name": "Игрок",
            "username": "unknown",
            "balance": 100,
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "high_score": 0,
            "join_date": datetime.now().strftime("%d.%m.%Y"),
            "daily_bonus": None,
            "achievements": [],
        }
    return players[user_id]

def get_kb(user_id: int):
    return admin_keyboard() if is_admin(user_id) else main_keyboard()

# ─────────────────────────── ОБРАБОТЧИКИ КОМАНД ───────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    user_states[user_id] = None
    p = get_player(user_id)
    p["name"] = message.from_user.first_name
    p["username"] = message.from_user.username or "Игрок"
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        p["balance"] += 50
        bot.send_message(message.chat.id, "🎁 +50 монет за реферала!")
    
    text = (
        "🦑 <b>SQUID GAME | ЛОББИ</b>\n\n"
        f"👤 Игрок: <b>{p['name']}</b>\n"
        f"💰 Баланс: <b>{p['balance']} монет</b>\n"
        f"⭐ Уровень: <b>{p['games_played'] // 5 + 1}</b>\n\n"
        "Выберите действие:"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_kb(message.chat.id))

@bot.message_handler(func=lambda m: m.text == "🎮 Игры")
def games_menu(message):
    text = (
        "🎮 <b>ВЫБЕРИТЕ ИГРУ</b>\n\n"
        "🟢 <b>Красный свет — Зелёный свет</b> — беги на зелёный!\n"
        "🍬 <b>Сахарные соты</b> — вырезай фигуру\n"
        "🎲 <b>Кости</b> — угадай чёт/нечет\n"
        "🔢 <b>Угадай число</b> — от 1 до 100"
    )
    bot.send_message(message.chat.id, text, reply_markup=games_keyboard())

# ── Баланс ──
@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(message):
    user_id = str(message.chat.id)
    p = get_player(user_id)
    
    # Ежедневный бонус
    today = datetime.now().strftime("%Y-%m-%d")
    bonus_available = p.get("daily_bonus") != today
    
    text = (
        "💰 <b>ВАШ СЧЁТ</b>\n\n"
        f"👤 <b>{p['name']}</b>\n"
        f"💎 Баланс: <b>{p['balance']} монет</b>\n"
        f"🎮 Игр: <b>{p['games_played']}</b>\n"
        f"🏆 Побед: <b>{p['wins']}</b> | 💀 Поражений: <b>{p['losses']}</b>\n"
        f"⭐ Рекорд: <b>{p['high_score']}</b>\n"
        f"📅 В игре с: {p.get('join_date', '—')}\n\n"
    )
    
    if bonus_available:
        text += "🎁 <b>Ежедневный бонус доступен!</b> Нажмите кнопку ниже:"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 ЗАБРАТЬ +25 МОНЕТ", callback_data="daily_bonus"))
        bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        text += "✅ Ежедневный бонус уже получен сегодня."
        bot.send_message(message.chat.id, text)

# ── Рейтинг ──
@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    if not players:
        bot.send_message(message.chat.id, "🏆 Пока нет игроков."); return
    sorted_players = sorted(players.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["👤"] * 7
    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
    for i, (uid, p) in enumerate(sorted_players):
        text += f"{medals[i]} <b>{p['name']}</b> — {p['balance']} монет\n"
    bot.send_message(message.chat.id, text)

# ── Промокод ──
@bot.message_handler(func=lambda m: m.text == "🎁 Промокод")
def promo_info(message):
    user_states[str(message.chat.id)] = "entering_promo"
    bot.send_message(message.chat.id, "🔑 Введите промокод:", reply_markup=remove_kb())

# ── Банк ──
@bot.message_handler(func=lambda m: m.text == "🏦 Банк")
def bank_menu(message):
    user_id = str(message.chat.id)
    p = get_player(user_id)
    dep = deposits.get(user_id, {"amount": 0, "date": None})
    
    text = (
        "🏦 <b>БАНК SQUID GAME</b>\n\n"
        f"💰 Ваш вклад: <b>{dep['amount']} монет</b>\n"
        f"📈 Процент: <b>5% в день</b>\n"
    )
    
    if dep["date"]:
        days_passed = (datetime.now() - dep["date"]).days
        text += f"📅 Дней во вкладе: <b>{days_passed}</b>\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Вложить", callback_data="bank_deposit"),
        types.InlineKeyboardButton("💸 Снять", callback_data="bank_withdraw"),
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ── Рулетка ──
@bot.message_handler(func=lambda m: m.text == "🎰 Рулетка")
def roulette_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎰 Крутить (10 монет)", callback_data="roulette_spin"),
        types.InlineKeyboardButton("❌ Выйти", callback_data="roulette_exit"),
    )
    text = (
        "🎰 <b>РУЛЕТКА</b>\n\n"
        "Сектора:\n"
        "🔴 x0 — проигрыш (40%)\n"
        "🟡 x2 — удвоение (30%)\n"
        "🟢 x3 — утроение (15%)\n"
        "🔵 x5 — x5 (10%)\n"
        "💎 ДЖЕКПОТ x10! (5%)\n\n"
        "Ставка: <b>10 монет</b>"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ── Перевод ──
@bot.message_handler(func=lambda m: m.text == "💸 Перевод")
def transfer_start(message):
    user_states[str(message.chat.id)] = "transferring"
    bot.send_message(
        message.chat.id,
        "💸 <b>ПЕРЕВОД МОНЕТ</b>\n\n"
        "Введите:\n<code>ID_игрока | СУММА</code>\n\n"
        "ID можно найти в рейтинге или спросить у друга.\n"
        "Для отмены нажмите /start",
        reply_markup=remove_kb()
    )

# ── Статистика ──
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    user_id = str(message.chat.id)
    p = get_player(user_id)
    total_players = len(players)
    total_coins = sum(p["balance"] for p in players.values())
    
    text = (
        "📊 <b>СТАТИСТИКА СЕРВЕРА</b>\n\n"
        f"👥 Игроков: <b>{total_players}</b>\n"
        f"💰 Всего монет: <b>{total_coins}</b>\n"
        f"🎁 Промокодов: <b>{len(promocodes)}</b>\n"
        f"🦑 Игр сыграно: <b>{sum(p['games_played'] for p in players.values())}</b>\n"
    )
    bot.send_message(message.chat.id, text)

# ── Новости ──
@bot.message_handler(func=lambda m: m.text == "📰 Новости")
def news(message):
    bot.send_message(message.chat.id, f"📰 <b>НОВОСТИ</b>\n\n{server_news}")

# ── Помощь ──
@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_cmd(message):
    text = (
        "🦑 <b>ПОМОЩЬ</b>\n\n"
        "🎮 <b>Игры:</b> Красный свет, Соты, Кости, Число\n"
        "🎰 <b>Рулетка:</b> Крути и выигрывай x10!\n"
        "🏦 <b>Банк:</b> Вклад под 5% в день\n"
        "💸 <b>Перевод:</b> Отправляй монеты друзьям\n"
        "🎁 <b>Промокоды:</b> Вводи и получай бонусы\n"
        "📅 <b>Бонус:</b> Ежедневный +25 монет\n\n"
        "Команды: /start, /players (админ)"
    )
    bot.send_message(message.chat.id, text)

# ── Админ-панель ──
@bot.message_handler(func=lambda m: m.text == "🔧 Админ" and is_admin(m.chat.id))
def admin_panel(message):
    bot.send_message(message.chat.id, "🔧 <b>АДМИН-ПАНЕЛЬ</b>", reply_markup=admin_panel_keyboard())

# ─────────────────────────── СОСТОЯНИЯ ───────────────────────────
@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "entering_promo")
def process_promo(message):
    user_states[str(message.chat.id)] = None
    code = message.text.strip().upper()
    kb = get_kb(message.chat.id)
    p = get_player(str(message.chat.id))
    
    if code in promocodes:
        promo = promocodes[code]
        if message.chat.id in promo.get('used_by', []):
            bot.send_message(message.chat.id, "❌ Вы уже использовали!", reply_markup=kb); return
        if promo['max_uses'] and len(promo.get('used_by', [])) >= promo['max_uses']:
            bot.send_message(message.chat.id, "❌ Промокод закончился!", reply_markup=kb); return
        
        p['balance'] += promo['reward']
        promo.setdefault('used_by', []).append(message.chat.id)
        bot.send_message(message.chat.id, f"🎁 +{promo['reward']} монет!\n💰 Баланс: {p['balance']}", reply_markup=kb)
    else:
        bot.send_message(message.chat.id, "❌ Не найден!", reply_markup=kb)

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "transferring")
def process_transfer(message):
    user_states[str(message.chat.id)] = None
    kb = get_kb(message.chat.id)
    try:
        parts = message.text.split("|")
        target_id = parts[0].strip()
        amount = int(parts[1].strip())
        sender = get_player(str(message.chat.id))
        
        if sender['balance'] < amount:
            bot.send_message(message.chat.id, "❌ Недостаточно монет!", reply_markup=kb); return
        if amount < 10:
            bot.send_message(message.chat.id, "❌ Минимальный перевод: 10 монет!", reply_markup=kb); return
        
        # Ищем получателя по ID
        found = None
        for uid in players:
            if uid.endswith(target_id):
                found = uid; break
        
        if not found:
            bot.send_message(message.chat.id, "❌ Игрок не найден!", reply_markup=kb); return
        
        sender['balance'] -= amount
        receiver = get_player(found)
        receiver['balance'] += amount
        
        bot.send_message(message.chat.id, f"✅ Переведено {amount} монет игроку #{target_id}!", reply_markup=kb)
        try:
            bot.send_message(int(found), f"💸 Игрок #{str(message.chat.id)[-4:]} перевёл вам <b>{amount} монет</b>!\n💰 Баланс: {receiver['balance']}")
        except: pass
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат! Пример: <code>1234 | 50</code>", reply_markup=kb)

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "creating_promo")
def process_create_promo(message):
    user_states[str(message.chat.id)] = None
    try:
        parts = message.text.split("|")
        code = parts[0].strip().upper()
        reward = int(parts[1].strip())
        max_uses = int(parts[2].strip()) if len(parts) > 2 else 0
        promocodes[code] = {"reward": reward, "max_uses": max_uses, "used_by": [], "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")}
        bot.send_message(message.chat.id, f"✅ Промокод <b>{code}</b> создан!", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "creating_news")
def process_create_news(message):
    global news_id_counter
    user_states[str(message.chat.id)] = None
    try:
        parts = message.text.split("|")
        tag = parts[0].strip()
        title = parts[1].strip()
        desc = parts[2].strip()
        date = parts[3].strip() if len(parts) > 3 else ""
        featured = parts[4].strip().lower() == "yes" if len(parts) > 4 else False
        tag_map = {"event": ("🔥 Событие", "tag-event"), "promo": ("🎁 Промокод", "tag-promo"), "update": ("🔄 Обновление", "tag-update"), "hot": ("🔴 Хит", "tag-hot")}
        tag_text, tag_class = tag_map.get(tag, ("📌 Новость", "tag-event"))
        news_id_counter += 1
        web_news.insert(0, {"id": news_id_counter, "tag": tag_class, "tag_text": tag_text, "title": title, "description": desc, "date": date, "featured": featured})
        bot.send_message(message.chat.id, f"✅ Новость создана!", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Ошибка формата!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "giving_coins")
def process_give_coins(message):
    user_states[str(message.chat.id)] = None
    try:
        parts = message.text.split("|")
        uid, amount = parts[0].strip(), int(parts[1].strip())
        for pid in players:
            if pid.endswith(uid):
                players[pid]['balance'] += amount
                bot.send_message(message.chat.id, f"✅ +{amount} монет игроку #{uid}", reply_markup=admin_keyboard())
                try: bot.send_message(int(pid), f"🎁 Админ выдал +{amount} монет!")
                except: pass
                return
        bot.send_message(message.chat.id, "❌ Игрок не найден!", reply_markup=admin_keyboard())
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "broadcasting")
def process_broadcast(message):
    user_states[str(message.chat.id)] = None
    sent = 0
    for uid in players:
        try:
            bot.send_message(int(uid), f"📢 <b>РАССЫЛКА</b>\n\n{message.text}")
            sent += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Отправлено {sent}/{len(players)}", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "depositing")
def process_deposit(message):
    user_states[str(message.chat.id)] = None
    kb = get_kb(message.chat.id)
    p = get_player(str(message.chat.id))
    try:
        amount = int(message.text.strip())
        if amount < 50:
            bot.send_message(message.chat.id, "❌ Минимальный вклад: 50 монет!", reply_markup=kb); return
        if p['balance'] < amount:
            bot.send_message(message.chat.id, "❌ Недостаточно монет!", reply_markup=kb); return
        p['balance'] -= amount
        deposits[str(message.chat.id)] = {"amount": amount, "date": datetime.now()}
        bot.send_message(message.chat.id, f"✅ Вклад {amount} монет!\n📈 +5% в день.", reply_markup=kb)
    except:
        bot.send_message(message.chat.id, "❌ Введите сумму числом!", reply_markup=kb)

# ─────────────────────────── CALLBACK-ОБРАБОТЧИКИ ───────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == "daily_bonus")
def daily_bonus(call):
    user_id = str(call.from_user.id)
    p = get_player(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if p.get("daily_bonus") == today:
        bot.answer_callback_query(call.id, "Уже получен сегодня!"); return
    
    p["daily_bonus"] = today
    p["balance"] += 25
    bot.answer_callback_query(call.id, "+25 монет!")
    bot.edit_message_text(
        f"💰 <b>БАЛАНС</b>\n\n💎 Баланс: <b>{p['balance']} монет</b>\n✅ Бонус получен!",
        call.message.chat.id, call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "bank_deposit")
def bank_deposit(call):
    user_states[str(call.from_user.id)] = "depositing"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "💰 Введите сумму вклада (мин. 50):", reply_markup=remove_kb())

@bot.callback_query_handler(func=lambda call: call.data == "bank_withdraw")
def bank_withdraw(call):
    user_id = str(call.from_user.id)
    dep = deposits.get(user_id, {"amount": 0, "date": None})
    p = get_player(user_id)
    
    if dep["amount"] == 0:
        bot.answer_callback_query(call.id, "У вас нет вклада!"); return
    
    days = max((datetime.now() - dep["date"]).days, 1)
    total = int(dep["amount"] * (1.05 ** days))
    p["balance"] += total
    deposits[user_id] = {"amount": 0, "date": None}
    
    bot.answer_callback_query(call.id, f"Снято {total} монет!")
    bot.send_message(call.message.chat.id, f"🏦 Снято <b>{total} монет</b> (вклад {dep['amount']} + проценты за {days} дн.)\n💰 Баланс: {p['balance']}")

@bot.callback_query_handler(func=lambda call: call.data == "roulette_spin")
def roulette_spin(call):
    user_id = str(call.from_user.id)
    p = get_player(user_id)
    
    if p["balance"] < 10:
        bot.answer_callback_query(call.id, "Недостаточно монет!"); return
    
    p["balance"] -= 10
    p["games_played"] += 1
    
    r = random.random()
    if r < 0.4:
        reward, emoji, msg = 0, "🔴", "x0 — проигрыш!"
    elif r < 0.7:
        reward, emoji, msg = 20, "🟡", "x2 — +20!"
    elif r < 0.85:
        reward, emoji, msg = 30, "🟢", "x3 — +30!"
    elif r < 0.95:
        reward, emoji, msg = 50, "🔵", "x5 — +50!"
    else:
        reward, emoji, msg = 100, "💎", "ДЖЕКПОТ x10 — +100!"
    
    p["balance"] += reward
    if reward > 0: p["wins"] += 1
    else: p["losses"] += 1
    
    bot.answer_callback_query(call.id, msg)
    bot.send_message(call.message.chat.id, f"🎰 {emoji} {msg}\n💰 Баланс: <b>{p['balance']} монет</b>")

@bot.callback_query_handler(func=lambda call: call.data == "roulette_exit")
def roulette_exit(call):
    bot.answer_callback_query(call.id, "До встречи!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ── Игры ──
@bot.callback_query_handler(func=lambda call: call.data == "game_rlgl")
def game_rlgl(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    p = get_player(user_id)
    p["games_played"] += 1
    
    if random.random() > 0.4:
        reward = random.randint(20, 100)
        p["balance"] += reward
        p["wins"] += 1
        p["high_score"] = max(p["high_score"], reward)
        text = f"🟢 <b>ЗЕЛЁНЫЙ СВЕТ!</b>\n\nВы добежали! 🏆\n💰 +{reward} монет\n💎 Баланс: {p['balance']}"
    else:
        p["losses"] += 1
        text = "🔴 <b>КРАСНЫЙ СВЕТ!</b>\n\nВас заметили! 💀\nВыбыли из игры."
    
    bot.send_message(call.message.chat.id, text, reply_markup=games_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "game_honeycomb")
def game_honeycomb(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    p = get_player(user_id)
    p["games_played"] += 1
    
    if random.random() > 0.3:
        reward = random.randint(30, 100)
        p["balance"] += reward
        p["wins"] += 1
        p["high_score"] = max(p["high_score"], reward)
        text = f"🍬 <b>СОТЫ ВЫРЕЗАНЫ!</b>\n\nУспешно! ✅\n💰 +{reward} монет\n💎 Баланс: {p['balance']}"
    else:
        p["losses"] += 1
        text = "🍬 <b>СОТЫ СЛОМАНЫ!</b>\n\nНеудача! 💥"
    
    bot.send_message(call.message.chat.id, text, reply_markup=games_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def game_dice(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🟢 ЧЁТ", callback_data="dice_even"),
        types.InlineKeyboardButton("🔴 НЕЧЕТ", callback_data="dice_odd"),
    )
    bot.send_message(call.message.chat.id, "🎲 <b>КОСТИ</b>\n\nВыберите чёт или нечет:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["dice_even", "dice_odd"])
def dice_bet(call):
    user_id = str(call.from_user.id)
    p = get_player(user_id)
    p["games_played"] += 1
    
    roll = random.randint(1, 6)
    is_even = roll % 2 == 0
    won = (call.data == "dice_even" and is_even) or (call.data == "dice_odd" and not is_even)
    dice_emojis = ['', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
    
    if won:
        reward = 20
        p["balance"] += reward
        p["wins"] += 1
        text = f"🎲 {dice_emojis[roll]} — {roll} ({'чёт' if is_even else 'нечет'})\n✅ Выигрыш! +{reward} монет\n💰 Баланс: {p['balance']}"
    else:
        p["losses"] += 1
        text = f"🎲 {dice_emojis[roll]} — {roll} ({'чёт' if is_even else 'нечет'})\n❌ Проигрыш!\n💰 Баланс: {p['balance']}"
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "game_guess")
def game_guess(call):
    bot.answer_callback_query(call.id)
    user_states[str(call.from_user.id)] = "guessing"
    
    # Генерируем число и сохраняем
    number = random.randint(1, 100)
    # Сохраняем в user_states (временно)
    user_states[str(call.from_user.id) + "_num"] = number
    user_states[str(call.from_user.id) + "_attempts"] = 0
    
    bot.send_message(call.message.chat.id, "🔢 Я загадал число от 1 до 100.\nУ вас 7 попыток!\n\nВведите число:", reply_markup=remove_kb())

@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id)) == "guessing")
def guess_number(message):
    user_id = str(message.chat.id)
    number = user_states.get(user_id + "_num", 0)
    attempts = user_states.get(user_id + "_attempts", 0) + 1
    user_states[user_id + "_attempts"] = attempts
    p = get_player(user_id)
    kb = get_kb(message.chat.id)
    
    try:
        guess = int(message.text.strip())
    except:
        bot.send_message(message.chat.id, "❌ Введите число!"); return
    
    if guess == number:
        p["games_played"] += 1
        reward = max(100 - attempts * 10, 10)
        p["balance"] += reward
        p["wins"] += 1
        p["high_score"] = max(p["high_score"], reward)
        user_states[user_id] = None
        bot.send_message(message.chat.id, f"🎉 <b>ПРАВИЛЬНО!</b> Это {number}!\n💰 +{reward} монет\n💎 Баланс: {p['balance']}", reply_markup=kb)
    elif attempts >= 7:
        p["games_played"] += 1
        p["losses"] += 1
        user_states[user_id] = None
        bot.send_message(message.chat.id, f"💀 <b>ПОПЫТКИ ЗАКОНЧИЛИСЬ!</b>\nЧисло было: {number}", reply_markup=kb)
    elif guess < number:
        bot.send_message(message.chat.id, f"📈 <b>БОЛЬШЕ!</b>\nПопыток: {attempts}/7")
    else:
        bot.send_message(message.chat.id, f"📉 <b>МЕНЬШЕ!</b>\nПопыток: {attempts}/7")

# Админские callback
@bot.callback_query_handler(func=lambda call: call.data == "admin_create_promo" and is_admin(call.from_user.id))
def admin_create_promo(call):
    bot.answer_callback_query(call.id)
    user_states[str(call.from_user.id)] = "creating_promo"
    bot.send_message(call.message.chat.id, "🎁 Формат: <code>КОД | НАГРАДА | МАКС</code>\nПример: <code>SQUID1 | 500 | 5</code>", reply_markup=remove_kb())

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_promo" and is_admin(call.from_user.id))
def admin_list_promo(call):
    bot.answer_callback_query(call.id)
    if not promocodes: bot.send_message(call.message.chat.id, "Нет промокодов."); return
    text = "📋 <b>ПРОМОКОДЫ:</b>\n\n"
    for code, p in promocodes.items():
        text += f"<b>{code}</b> — {p['reward']} монет | {len(p.get('used_by',[]))}/{p['max_uses'] if p['max_uses'] else '∞'}\n"
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_create_news" and is_admin(call.from_user.id))
def admin_create_news(call):
    bot.answer_callback_query(call.id)
    user_states[str(call.from_user.id)] = "creating_news"
    bot.send_message(call.message.chat.id, "📰 Формат: <code>ТЕГ | ЗАГОЛОВОК | ОПИСАНИЕ | ДАТА | FEATURED</code>", reply_markup=remove_kb())

@bot.callback_query_handler(func=lambda call: call.data == "admin_give_coins" and is_admin(call.from_user.id))
def admin_give_coins(call):
    bot.answer_callback_query(call.id)
    user_states[str(call.from_user.id)] = "giving_coins"
    bot.send_message(call.message.chat.id, "💰 Формат: <code>ID | СУММА</code>", reply_markup=remove_kb())

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats" and is_admin(call.from_user.id))
def admin_stats(call):
    bot.answer_callback_query(call.id)
    text = f"📊 <b>СТАТИСТИКА</b>\n\n👥 Игроков: <b>{len(players)}</b>\n💰 Монет: <b>{sum(p['balance'] for p in players.values())}</b>\n🎮 Игр: <b>{sum(p['games_played'] for p in players.values())}</b>\n⏰ Запущен: {bot_started}"
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast" and is_admin(call.from_user.id))
def admin_broadcast(call):
    bot.answer_callback_query(call.id)
    user_states[str(call.from_user.id)] = "broadcasting"
    bot.send_message(call.message.chat.id, "📢 Введите текст рассылки:", reply_markup=remove_kb())

# ─────────────────────────── КОМАНДЫ ───────────────────────────
@bot.message_handler(commands=['players'])
def cmd_players(message):
    if not is_admin(message.chat.id): return
    if not players: bot.send_message(message.chat.id, "Нет игроков."); return
    text = "📋 <b>ИГРОКИ:</b>\n\n"
    for uid, p in list(players.items())[:20]:
        text += f"<code>{uid[-4:]}</code> — {p['name']} | {p['balance']} монет\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: True)
def fallback(message):
    kb = get_kb(message.chat.id)
    bot.send_message(message.chat.id, "Используйте кнопки меню или /start", reply_markup=kb)

# ─────────────────────────── FLASK ───────────────────────────
@app.route('/api/news')
def api_news():
    return jsonify(web_news)

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/')
def index():
    return render_template('landing.html')

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
    logger.info("🦑 Запуск Squid Game бота...")
    Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
