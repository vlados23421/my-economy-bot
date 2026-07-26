import os
import telebot
import random
import requests
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
from telebot import types

# --- 1. ВЕБ-СЕРВЕР ДЛЯ UPTIME НА RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Бот активен и работает 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)

# --- 2. ИНИЦИАЛИЗАЦИЯ БОТА И ДАННЫХ SUPABASE ---
TOKEN = os.environ.get("8957594048:AAFmdWyLWYxDNjE7tdw1xBfZVYjAK7Qjnhs")
ADMIN_ID = 8915047087  # !!! ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЙ TELEGRAM ID !!!

bot = telebot.TeleBot(TOKEN)

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Временное хранилище для создания промокодов админом
admin_states = {}

# --- 3. ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ---
def get_user(user_id, username):
    url = f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}"
    res = requests.get(url, headers=HEADERS).json()
    if not res:
        data = {"user_id": user_id, "username": username or f"id{user_id}", "balance": 500.0, "euros": 0.0, "last_daily": None, "last_mine": None}
        requests.post(f"{SUPABASE_URL}/rest/v1/users", json=data, headers=HEADERS)
        return data
    return res[0] if isinstance(res, list) and res else res

def update_user(user_id, updates):
    url = f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}"
    requests.patch(url, json=updates, headers=HEADERS)

# --- 4. КОМАНДЫ ЭКОНОМИКИ ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    get_user(message.from_user.id, message.from_user.username)
    text = (f"👋 Привет, {message.from_user.first_name}!\n"
            f"🤖 Добро пожаловать в игрового бота экономики.\n\n"
            f"⛏ /mine — Работать в шахте\n"
            f"💷 /daily — Получить ежедневный бонус\n"
            f"📊 /stats — Посмотреть баланс и Евро\n"
            f"🎟 /promo [код] — Активировать промокод")
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['stats', 'profile', 'профиль', 'статистика'])
def view_stats(message):
    user = get_user(message.from_user.id, message.from_user.username)
    text = (f"📊 *Статистика игрока @{user['username']}:*\n\n"
            f"💰 *Баланс:* {user['balance']:.2f} руб.\n"
            f"💶 *Евры:* {user['euros']:.2f} EUR")
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['daily', 'бонус'])
def get_daily(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    now = datetime.now()
    
    if user.get('last_daily'):
        last_daily = datetime.strptime(user['last_daily'], '%Y-%m-%d %H:%M:%S')
        if now - last_daily < timedelta(days=1):
            time_left = timedelta(days=1) - (now - last_daily)
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            bot.reply_to(message, f"❌ Вы уже брали бонус. Приходите через {hours}ч {minutes}м.")
            return

    reward = random.randint(100, 500)
    update_user(user_id, {"balance": user['balance'] + reward, "last_daily": now.strftime('%Y-%m-%d %H:%M:%S')})
    bot.reply_to(message, f"💷 Вы получили ежедневный бонус: *{reward} руб.*!", parse_mode='Markdown')

@bot.message_handler(commands=['mine', 'шахта'])
def go_mining(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    now = datetime.now()
    
    if user.get('last_mine'):
        last_mine = datetime.strptime(user['last_mine'], '%Y-%m-%d %H:%M:%S')
        if now - last_mine < timedelta(minutes=5):
            bot.reply_to(message, "⏳ Ваши руки устали. В шахту можно ходить раз в 5 минут!")
            return
            
    mined_money = random.randint(10, 80)
    mined_euros = round(random.uniform(0.1, 1.5), 2) if random.random() < 0.3 else 0.0
    
    update_user(user_id, {"balance": user['balance'] + mined_money, "euros": user['euros'] + mined_euros, "last_mine": now.strftime('%Y-%m-%d %H:%M:%S')})
    
    msg = f"⛏ Вы спустились в шахту и добыли:\n💵 Рубли: *+{mined_money} руб.*"
    if mined_euros > 0:
        msg += f"\n💶 Евры: *+{mined_euros} EUR*"
    bot.reply_to(message, msg, parse_mode='Markdown')

# --- 5. ИГРОКИ: АКТИВАЦИЯ ПРОМОКОДА ИЗ ОБЛАКА ---
@bot.message_handler(commands=['promo', 'промо'])
def use_promo(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    try:
        code = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "Введите промокод: `/promo КОД`", parse_mode='Markdown')
        return

    # Ищем промокод в базе данных Supabase
    url = f"{SUPABASE_URL}/rest/v1/promos?code=eq.{code}"
    res = requests.get(url, headers=HEADERS).json()
    
    if not res:
        bot.reply_to(message, "❌ Такой промокод не найден или устарел.")
        return
        
    promo = res[0]
    if promo['uses'] <= 0:
        bot.reply_to(message, "❌ Этот промокод уже закончился!")
        return

    # Начисляем валюту в зависимости от настроек промокода
    if promo['currency'] == 'euros':
        update_user(user_id, {"euros": user['euros'] + promo['reward']})
        bot.reply_to(message, f"🎉 Промокод активирован! Вам зачислено *+{promo['reward']} EUR*.", parse_mode='Markdown')
    else:
        update_user(user_id, {"balance": user['balance'] + promo['reward']})
        bot.reply_to(message, f"🎉 Промокод активирован! Вам зачислено *+{promo['reward']} руб.*.", parse_mode='Markdown')

    # Уменьшаем количество оставшихся использований на 1
    requests.patch(f"{SUPABASE_URL}/rest/v1/promos?code=eq.{code}", json={"uses": promo['uses'] - 1}, headers=HEADERS)

# --- 6. АДМИН-ПАНЕЛЬ (ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА) ---

@bot.message_handler(commands=['admin', 'админка'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Вы не являетесь администратором.")
        return
        
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🎟 Создать промокод", callback_data="create_promo")
    btn2 = types.InlineKeyboardButton("🎉 Запустить розыгрыш", callback_data="start_giveaway_btn")
    markup.add(btn1, btn2)
    
    bot.send_message(message.chat.id, "🛠 *Добро пожаловать в панель администратора!*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "create_promo":
        bot.send_message(call.message.chat.id, "✍ Введите данные промокода через пробел в формате:\n\n`КОД СУММА ВАЛЮТА(balance/euros) КОЛ-ВО_АКТИВАЦИЙ`\n\n*Пример:* `CRAZY2026 1000 balance 15`", parse_mode='Markdown')
        admin_states[call.from_user.id] = "waiting_promo"
        bot.answer_callback_query(call.id)
        
    elif call.data == "start_giveaway_btn":
        bot.answer_callback_query(call.id)
        # Имитируем вызов команды розыгрыша
        class FakeMessage:
            def __init__(self, chat_id, from_user):
                self.chat = chat_id
                self.from_user = from_user
        start_giveaway(FakeMessage(call.message.chat, call.from_user))

# Обработка ввода параметров промокода от админа
@bot.message_handler(func=lambda msg: admin_states.get(msg.from_user.id) == "waiting_promo")
def save_promo_from_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        code = args[0]
        reward = float(args[1])
        currency = args[2]  # 'balance' или 'euros'
        uses = int(args[3])
        
        if currency not in ['balance', 'euros']:
            bot.reply_to(message, "❌ Ошибка! Валюта должна быть либо `balance`, либо `euros`.")
            return

        # Сохраняем в Supabase
        data = {"code": code, "reward": reward, "currency": currency, "uses": uses}
        requests.post(f"{SUPABASE_URL}/rest/v1/promos", json=data, headers=HEADERS)
        
        bot.reply_to(message, f"✅ Промокод *{code}* успешно создан на {uses} активаций!", parse_mode='Markdown')
        admin_states[message.from_user.id] = None
    except Exception:
        bot.reply_to(message, "❌ Ошибка ввода! Проверьте формат:\n`КОД СУММА ВАЛЮТА КОЛ-ВО`")

@bot.message_handler(commands=['giveaway', 'розыгрыш'])
def start_giveaway(message):
    if message.from_user.id != ADMIN_ID:
        return
    res = requests.get(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS).json()
    if not res:
        bot.send_message(message.chat.id, "В базе данных еще нет игроков.")
        return
        
    winner = random.choice(res)
    prize = random.randint(1000, 5000)
    update_user(winner['user_id'], {"balance": winner['balance'] + prize})
    bot.send_message(message.chat.id, f"🎉 *ВНИМАНИЕ, РОЗЫГРЫШ!* 🎉\n\nПобедителем становится @{winner['username']}!\nОн получает приз: *{prize} рублей*! 💷", parse_mode='Markdown')

# --- ЗАПУСК ПРОЕКТА ---
def run_bot():
    print("Бот Telegram запущен...")
    bot.infinity_polling()

if __name__ == '__main__':
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    print("Запуск веб-сервера...")
    run_flask()
