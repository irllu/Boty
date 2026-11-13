import sqlite3
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from aiogram.utils import executor
import datetime
import os

API_TOKEN = '8118295235:AAGC_avEdUmVgEtsDyObA3Mo7hsQEx4QvRo'  # <-- вставь свой токен

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# База данных
conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    project TEXT DEFAULT '',
    target REAL DEFAULT 0,
    daily_profit REAL DEFAULT 0
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS trades (
    user_id INTEGER,
    date TEXT,
    profit REAL
)
''')
conn.commit()

# === Команды установки ===

@dp.message_handler(commands=['set_project'])
async def set_project(message: types.Message):
    project = message.get_args()
    cursor.execute('INSERT OR IGNORE INTO settings (user_id) VALUES (?)', (message.from_user.id,))
    cursor.execute('UPDATE settings SET project = ? WHERE user_id = ?', (project, message.from_user.id))
    conn.commit()
    await message.reply(f"✅ Проект создан: {project}")

@dp.message_handler(commands=['set_target'])
async def set_target(message: types.Message):
    try:
        target = float(message.get_args())
        cursor.execute('INSERT OR IGNORE INTO settings (user_id) VALUES (?)', (message.from_user.id,))
        cursor.execute('UPDATE settings SET target = ? WHERE user_id = ?', (target, message.from_user.id))
        conn.commit()
        await message.reply(f"✅ Цель установлена: {target} USDT")
    except ValueError:
        await message.reply("❌ Введите сумму. Пример: /set_target 10000")

@dp.message_handler(commands=['set_profit'])
async def set_profit(message: types.Message):
    try:
        profit = float(message.get_args())
        cursor.execute('INSERT OR IGNORE INTO settings (user_id) VALUES (?)', (message.from_user.id,))
        cursor.execute('UPDATE settings SET daily_profit = ? WHERE user_id = ?', (profit, message.from_user.id))
        conn.commit()
        await message.reply(f"✅ Профит в день: {profit} USDT")
    except ValueError:
        await message.reply("❌ Введите сумму. Пример: /set_profit 200")

# === Команда добавления сделки ===

@dp.message_handler(commands=['add_trade'])
async def add_trade(message: types.Message):
    try:
        value = float(message.get_args())
        today = datetime.date.today().isoformat()
        cursor.execute('INSERT INTO trades (user_id, date, profit) VALUES (?, ?, ?)',
                       (message.from_user.id, today, value))
        conn.commit()
        await message.reply(f"✅ Сделка добавлена: {value} USDT")
    except ValueError:
        await message.reply("❌ Введите прибыль или убыток. Пример: /add_trade 150")

# === Прогресс ===

@dp.message_handler(commands=['progress'])
async def show_progress(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('SELECT project, target FROM settings WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if not result:
        await message.reply("❌ Сначала установите проект и цель.")
        return

    project, target = result
    cursor.execute('SELECT SUM(profit), COUNT(DISTINCT date) FROM trades WHERE user_id = ?', (user_id,))
    total, days = cursor.fetchone()
    total = total or 0
    days = days or 0
    remaining = target - total
    percent = (total / target * 100) if target else 0

    # Генерация графика
    cursor.execute('SELECT date, SUM(profit) FROM trades WHERE user_id = ? GROUP BY date', (user_id,))
    data = cursor.fetchall()
    dates = [row[0] for row in data]
    profits = [row[1] for row in data]
    cumulative = []
    running_total = 0
    for profit in profits:
        running_total += profit
        cumulative.append(running_total)

    # График
    if dates:
        plt.figure(figsize=(10, 4))
        plt.plot(dates, cumulative, marker='o', color='blue')
        plt.title(f"Прогресс: {project}")
        plt.xlabel("Дата")
        plt.ylabel("Отторговано (USDT)")
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = f"progress_{user_id}.png"
        plt.savefig(path)
        plt.close()
    else:
        path = None

    # Ответ
    caption = f"""📈 Прогресс: <b>{project}</b>
💰 Цель: <b>{target} USDT</b>
📅 Торговых дней: <b>{days}</b>
📊 Отторговано: <b>{total:.2f} USDT</b> ({percent:.1f}%)
🎯 Осталось: <b>{remaining:.2f} USDT</b>
"""
    if path:
        await bot.send_photo(chat_id=message.chat.id, photo=InputFile(path), caption=caption, parse_mode="HTML")
        os.remove(path)
    else:
        await message.reply(caption, parse_mode="HTML")

# === Запуск бота ===

if __name__ == '__main__':
    print("✅")
    executor.start_polling(dp, skip_updates=True)