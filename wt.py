"""
Telegram-бот для ведения статистики сделок.
Работает на aiogram >= 3.7.0 и Python 3.12+.
"""

import asyncio, os, sqlite3
from datetime import date

import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types.input_file import FSInputFile
from aiogram.client.default import DefaultBotProperties

API_TOKEN = "8118295235:AAGC_avEdUmVgEtsDyObA3Mo7hsQEx4QvRo"  # <-- ВСТАВЬ СЮДА СВОЙ ТОКЕН

# ───── Настройка aiogram 3.7+ ─────
bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
rt = Router()
dp.include_router(rt)

# ───── База данных SQLite ─────
db = sqlite3.connect("trading_bot.db")
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    project TEXT DEFAULT '',
    target REAL DEFAULT 0,
    daily_profit REAL DEFAULT 0
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS trades (
    user_id INTEGER,
    date TEXT,
    profit REAL
)
""")
db.commit()

# ───── Вспомогательные функции ─────
def _split_arg(text: str) -> str | None:
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else None

def _ensure_user(uid: int):
    cur.execute("INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (uid,))
    db.commit()

# ───── Команды ─────
@rt.message(Command("set_project"))
async def set_project(msg: types.Message):
    project = _split_arg(msg.text)
    if not project:
        return await msg.answer("Пример: <code>/set_project Binance</code>")
    _ensure_user(msg.from_user.id)
    cur.execute("UPDATE settings SET project=? WHERE user_id=?", (project, msg.from_user.id))
    db.commit()
    await msg.answer(f"✅ Проект создан: <b>{project}</b>")

@rt.message(Command("set_target"))
async def set_target(msg: types.Message):
    arg = _split_arg(msg.text)
    try:
        value = float(arg)
    except (TypeError, ValueError):
        return await msg.answer("Пример: <code>/set_target 10000</code>")
    _ensure_user(msg.from_user.id)
    cur.execute("UPDATE settings SET target=? WHERE user_id=?", (value, msg.from_user.id))
    db.commit()
    await msg.answer(f"✅ Цель: <b>{value} USDT</b>")

@rt.message(Command("set_profit"))
async def set_profit(msg: types.Message):
    arg = _split_arg(msg.text)
    try:
        value = float(arg)
    except (TypeError, ValueError):
        return await msg.answer("Пример: <code>/set_profit 200</code>")
    _ensure_user(msg.from_user.id)
    cur.execute("UPDATE settings SET daily_profit=? WHERE user_id=?", (value, msg.from_user.id))
    db.commit()
    await msg.answer(f"✅ Профит: <b>{value} USDT</b>")

@rt.message(Command("add_trade"))
async def add_trade(msg: types.Message):
    arg = _split_arg(msg.text)
    try:
        value = float(arg)
    except (TypeError, ValueError):
        return await msg.answer("Пример: <code>/add_trade 150</code>")
    today = date.today().isoformat()
    cur.execute("INSERT INTO trades (user_id, date, profit) VALUES (?, ?, ?)", (msg.from_user.id, today, value))
    db.commit()
    await msg.answer(f"💾 Сделка добавлена: <b>{value:+.2f} USDT</b>")

@rt.message(Command("progress"))
async def progress(msg: types.Message):
    uid = msg.from_user.id
    cur.execute("SELECT project, target FROM settings WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if not row:
        return await msg.answer("Сначала задайте проект и цель.")

    project, target = row
    cur.execute("SELECT SUM(profit), COUNT(DISTINCT date) FROM trades WHERE user_id=?", (uid,))
    total, days = cur.fetchone()
    total = total or 0
    days = days or 0
    remaining = target - total
    percent = (total / target * 100) if target else 0

    cur.execute("SELECT date, SUM(profit) FROM trades WHERE user_id=? GROUP BY date", (uid,))
    data = cur.fetchall()
    dates = [row[0] for row in data]
    profits = [row[1] for row in data]
    cumulative = []
    acc = 0
    for p in profits:
        acc += p
        cumulative.append(acc)

    image_path = None
    if dates:
        plt.figure(figsize=(10, 4))
        plt.plot(dates, cumulative, marker='o', color='blue')
        plt.title(f"Прогресс: {project}")
        plt.xlabel("Дата")
        plt.ylabel("Отторговано, USDT")
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        image_path = f"progress_{uid}.png"
        plt.savefig(image_path)
        plt.close()

    caption = (f"📈 <b>{project}</b>\n"
               f"💰 Цель: <b>{target} USDT</b>\n"
               f"📅 Торговых дней: <b>{days}</b>\n"
               f"📊 Отторговано: <b>{total:.2f} USDT</b> ({percent:.1f}%)\n"
               f"🎯 Осталось: <b>{remaining:.2f} USDT</b>")
    
    if image_path:
        await msg.answer_photo(FSInputFile(image_path), caption=caption)
        os.remove(image_path)
    else:
        await msg.answer(caption)

# ───── Запуск ─────
async def main():
    print("✅ Бот")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())