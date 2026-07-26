import os
import telebot
import random
import requests
from datetime import datetime, timedelta

# --- 1. ИНИЦИАЛИЗАЦИЯ БОТА И ДАННЫХ SUPABASE ---
# На FPS.ms мы пропишем эти токены прямо в панели управления
TOKEN = "8957594048:AAFmdWyLWYxDNjE7tdw1xBfZVYjAK7Qjnhs" # Вставьте сюда ваш токен от BotFather)
ADMIN_ID = 8915047087  # !!! ЗАМЕНИТЕ НА ВАШ REAL TELEGRAM ID !!!

bot = telebot.TeleBot(TOKEN)

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- 2. ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ---
def get_user(user_id, username):
    """Получает игрока или создает его со стартовыми 500 рублями"""
    url = f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}"
    res = requests.get(url, headers=HEADERS).json()
    
    if not res:
        data = {
            "user_id": user_id,
            "username": username or f"id{user_id}",
            "balance": 500.0,
            "euros": 0.0,
            "last_daily": None,
            "last_mine": None
        }
        requests.post(f"{SUPABASE_URL}/rest/v1/users", json=data, headers=HEADERS)
        return data
    return res[0]

def update_user(user_id, updates):
    """Обновляет любые поля игрока в облаке Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}"
    requests.patch(url, json=updates, headers=HEADERS)

# --- 3. ИГРОВЫЕ КОМАНДЫ ЭКОНОМИКИ ---

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
    
    if user['last_daily']:
        last_daily = datetime.strptime(user['last_daily'], '%Y-%m-%d %H:%M:%S')
        if now - last_daily < timedelta(days=1):
            time_left = timedelta(days=1) - (now - last_daily)
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            bot.reply_to(message, f"❌ Вы уже брали бонус. Приходите через {hours}ч {minutes}м.")
            return

    reward = random.randint(100, 500)
    new_balance = user['balance'] + reward
    update_user(user_id, {
        "balance": new_balance,
        "last_daily": now.strftime('%Y-%m-%d %H:%M:%S')
    })
    bot.reply_to(message, f"💷 Вы получили ежедневный бонус: *{reward} руб.*!", parse_mode='Markdown')

@bot.message_handler(commands=['mine', 'шахта'])
def go_mining(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    now = datetime.now()
    
    if user['last_mine']:
        last_mine = datetime.strptime(user['last_mine'], '%Y-%m-%d %H:%M:%S')
        if now - last_mine < timedelta(minutes=5):
            bot.reply_to(message, "⏳ Ваши руки устали. В шахту можно ходить раз в 5 минут!")
            return
            
    mined_money = random.randint(10, 80)
    mined_euros = round(random.uniform(0.1, 1.5), 2) if random.random() < 0.3 else 0.0
    
    new_balance = user['balance'] + mined_money
    new_euros = user['euros'] + mined_euros
    
    update_user(user_id, {
        "balance": new_balance,
        "euros": new_euros,
        "last_mine": now.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    msg = f"⛏ Вы спустились в шахту и добыли:\n💵 Рубли: *+{mined_money} руб.*"
    if mined_euros > 0:
        msg += f"\n💶 Евры: *+{mined_euros} EUR*"
    bot.reply_to(message, msg, parse_mode='Markdown')

# --- 4. АДМИНКА: РОЗЫГРЫШ И ПРОМОКОДЫ ---

@bot.message_handler(commands=['promo', 'промо'])
def use_promo(message):
    user_id = message.from_user.id
    try:
        code = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "Введите промокод: `/promo КОД`", parse_mode='Markdown')
        return

    if code.lower() == "start2026":
        user = get_user(user_id, message.from_user.username)
        update_user(user_id, {"balance": user['balance'] + 1000})
        bot.reply_to(message, "🎉 Вы активировали промокод! Зачислено +1000 рублей.")
    else:
        bot.reply_to(message, "❌ Такой промокод не найден.")

@bot.message_handler(commands=['giveaway', 'розыгрыш'])
def start_giveaway(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    res = requests.get(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS).json()
    if not res:
        bot.reply_to(message, "В базе данных еще нет игроков.")
        return
        
    winner = random.choice(res)
    prize = random.randint(1000, 5000)
    
    update_user(winner['user_id'], {"balance": winner['balance'] + prize})
    bot.send_message(message.chat.id, f"🎉 *ВНИМАНИЕ, РОЗЫГРЫШ!* 🎉\n\nПобедителем становится @{winner['username']}!\nОн получает приз: *{prize} рублей*! 💷", parse_mode='Markdown')

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling()
