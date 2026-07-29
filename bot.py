import os
import logging
import json
from flask import Flask, request, abort, render_template
import telebot
from telebot import types

# ─────────────────────────── ПЕРЕМЕННЫЕ ───────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")  # https://your-app.onrender.com

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# Простая база игроков (в реальном проекте — БД)
players = {}

# ─────────────────────────── КЛАВИАТУРЫ ───────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🦑 Играть", "💰 Баланс")
    markup.add("🏆 Рейтинг", "📢 Пригласить")
    markup.add("ℹ️ Правила")
    return markup

def webapp_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "🦑 ИГРАТЬ В SQUID GAME",
        web_app=types.WebAppInfo(url=f"{WEB_APP_URL}/game")
    ))
    return markup

# ─────────────────────────── ОБРАБОТЧИКИ ───────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    
    if user_id not in players:
        players[user_id] = {
            "name": message.from_user.first_name,
            "username": message.from_user.username,
            "balance": 0,
            "games_played": 0,
            "high_score": 0,
        }
    
    text = (
        f"🦑 <b>SQUID GAME</b>\n\n"
        f"Добро пожаловать, Игрок #{user_id[-4:]}!\n\n"
        "🎮 <b>Доступные игры:</b>\n"
        "🟢 Красный свет — Зелёный свет\n"
        "🍬 Сахарные соты\n"
        "🎲 Кости\n"
        "🔢 Угадай число\n\n"
        "💰 Выигрывай валюту и стань лучшим!"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🦑 Играть")
def play_game(message):
    bot.send_message(
        message.chat.id,
        "🦑 Выберите игру и начните играть прямо сейчас!",
        reply_markup=webapp_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(message):
    user_id = str(message.chat.id)
    player = players.get(user_id, {"balance": 0, "games_played": 0, "high_score": 0})
    
    text = (
        f"💰 <b>Ваш счёт</b>\n\n"
        f"Игрок: <b>{player['name']}</b>\n"
        f"Баланс: <b>{player['balance']} монет</b>\n"
        f"Сыграно игр: <b>{player['games_played']}</b>\n"
        f"Рекорд: <b>{player['high_score']}</b>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    if not players:
        bot.send_message(message.chat.id, "🏆 Пока нет игроков.")
        return
    
    sorted_players = sorted(players.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    
    medals = ["🥇", "🥈", "🥉"] + ["👤"] * 7
    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
    
    for i, (uid, p) in enumerate(sorted_players):
        name = p['name'] or f"Игрок {uid[-4:]}"
        text += f"{medals[i]} <b>{name}</b> — {p['balance']} монет\n"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📢 Пригласить")
def invite(message):
    user_id = str(message.chat.id)
    text = (
        "📢 <b>Пригласи друга!</b>\n\n"
        f"Отправь ему эту ссылку:\n"
        f"<code>https://t.me/{bot.get_me().username}?start=ref{user_id[-4:]}</code>\n\n"
        "За каждого друга вы получаете <b>+50 монет</b>!"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Правила")
def rules(message):
    text = (
        "🦑 <b>ПРАВИЛА ИГРЫ</b>\n\n"
        "🎮 Играйте в мини-игры и зарабатывайте монеты.\n\n"
        "🟢 <b>Красный свет — Зелёный свет:</b>\n"
        "Нажимайте ЗЕЛЁНЫЙ, не двигайтесь на КРАСНЫЙ.\n\n"
        "🍬 <b>Сахарные соты:</b>\n"
        "Вырезайте фигуру, не сломав её.\n\n"
        "🎲 <b>Кости:</b>\n"
        "Угадайте чёт/нечет и удвойте ставку.\n\n"
        "🏆 Побеждает тот, у кого больше монет!"
    )
    bot.send_message(message.chat.id, text)

# Приём данных из Web App
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    user_id = str(message.chat.id)
    data = json.loads(message.web_app_data.data)
    
    game = data.get('game')
    score = data.get('score', 0)
    reward = data.get('reward', 0)
    
    if user_id in players:
        players[user_id]['balance'] += reward
        players[user_id]['games_played'] += 1
        players[user_id]['high_score'] = max(players[user_id]['high_score'], score)
    
    bot.send_message(
        message.chat.id,
        f"🎉 <b>Игра завершена!</b>\n\n"
        f"🎮 Игра: <b>{game}</b>\n"
        f"📊 Очки: <b>{score}</b>\n"
        f"💰 Награда: <b>+{reward} монет</b>\n"
        f"💎 Баланс: <b>{players[user_id]['balance']} монет</b>",
        reply_markup=webapp_keyboard()
    )

# ─────────────────────────── FLASK + WEB APP ───────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

if __name__ == "__main__":
    from threading import Thread
    
    # Запускаем polling в отдельном потоке
    Thread(target=bot.infinity_polling).start()
    
    # Запускаем Flask для Web App
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
