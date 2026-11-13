import asyncio
import datetime
from io import BytesIO

import aiohttp
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Настройки
COOLDOWN_SECONDS = 666
user_cooldowns = {}

TIMEFRAMES = {
    "15хв": ("15m", "15m"),
    "1г": ("1H", "1H"),
    "4г": ("4H", "4H"),
    "1день": ("1D", "1D"),
}


# Получение свечей с OKX
async def get_okx_candles(symbol="PI-USDT", bar="1H", limit=300):
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": symbol, "bar": bar, "limit": limit}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            if data["code"] != "0":
                raise Exception("Ошибка получения данных с OKX")

            candles = [
                (
                    datetime.datetime.fromtimestamp(int(c[0]) / 1000),
                    float(c[1]),  # open
                    float(c[2]),  # high
                    float(c[3]),  # low
                    float(c[4]),  # close
                )
                for c in reversed(data["data"])
            ]
            return candles


# Построение графика
def generate_candle_plot(data, label="1H", bar="1H"):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_facecolor("#e0e0e0")
    fig.patch.set_facecolor("#e0e0e0")

    for candle in data:
        time, open_, high, low, close = candle
        color = "white" if close > open_ else "black"
        edge_color = "black"

        width_minutes = {"15m": 15, "1H": 60, "4H": 240, "1D": 1440}[bar]
        body_width = datetime.timedelta(minutes=width_minutes * 0.6)

        ax.plot([time, time], [low, high], color=edge_color, linewidth=1)

        ax.add_patch(plt.Rectangle(
            (time - body_width / 2, min(open_, close)),
            body_width,
            abs(close - open_),
            facecolor=color,
            edgecolor=edge_color,
            linewidth=1
        ))

    ax.set_title(f"PI/USDT ({label})", fontsize=14)
    ax.set_xlabel("Час")
    ax.set_ylabel("Ціна ($)")
    ax.grid(True)
    fig.autofmt_xdate()

    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# Команда /p
async def p(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.datetime.now()

    if user_id in user_cooldowns:
        elapsed = (now - user_cooldowns[user_id]).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            await update.message.reply_text(f"⏳ Зачекайте {remaining} сек. перед повторною командою.")
            return

    user_cooldowns[user_id] = now

    keyboard = [[InlineKeyboardButton(tf, callback_data=tf) for tf in TIMEFRAMES]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Таймфрейм графіка PI/USDT:", reply_markup=markup)


# Обработка нажатий
async def handle_timeframe_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        return

    tf_label = query.data
    tf_bar, tf_name = TIMEFRAMES[tf_label]

    try:
        candles = await get_okx_candles("PI-USDT", tf_bar, 300)

        if tf_bar in ("1H", "4H"):
            limit_date = datetime.datetime.utcnow() - datetime.timedelta(days=3)
            candles = [c for c in candles if c[0] >= limit_date]

        last_price = candles[-1][4]
        plot = generate_candle_plot(candles, tf_name, tf_bar)

        caption = (
            f"📊 Графік PI/USDT\n"
            f"🕒 Таймфрейм: <b>{tf_label}</b>\n"
            f"💰 Ціна: <b>{last_price:.4f}$</b>"
        )
        await query.message.reply_photo(photo=plot, caption=caption, parse_mode=ParseMode.HTML)

    except Exception as e:
        print(f"[ERROR] {e}")
        await query.message.reply_text("⚠️ Не вдалося отримати дані.")


# Команда /s
async def s(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>Біржі для продажу:</b>\n"
        "<a href='https://www.bitget.com/referral/register?clacCode=ZDLNNGBC'>Bitget</a>\n"
        "<a href='https://okx.com/join/19462805'>OKX</a>\n"
        "<a href='https://promote.mexc.com/r/Aysfsoz7'>MEXC</a>\n"
        "<a href='https://www.gate.com/signup/VLRGUG1FBA'>Gate</a>\n"
    )
    image_url = "https://drive.google.com/uc?export=view&id=1hykojtFtvVfdzIxacRhbolcLF38mprFf"
    await update.message.reply_photo(
        photo=image_url,
        caption=text,
        parse_mode=ParseMode.HTML
    )


# Команда /r
async def r(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 <a href='https://minepi.com/irllu'>Pi Network (Реєстрація)</a>",
        parse_mode="HTML"
    )


# Запуск бота
async def start_bot():
    TOKEN = "7824375188:AAHKwklj_pD8vv2UZWyMFAcIftYEm2tiuIs"  # ← вставь свой токен сюда
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("p", p))
    app.add_handler(CommandHandler("s", s))
    app.add_handler(CommandHandler("r", r))
    app.add_handler(CallbackQueryHandler(handle_timeframe_selection))

    print("✅")
    await app.run_polling()


# Для запуска в PyCharm
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(start_bot())

###########################################################################
# Работает на aiogram >= 3.7.0 и Python 3.12+.

import asyncio, os, sqlite3
from datetime import date

import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types.input_file import FSInputFile
from aiogram.client.default import DefaultBotProperties

API_TOKEN = "8118295235:AAGC_avEdUmVgEtsDyObA3Mo7hsQEx4QvRo" 

# ───── Настройка aiogram 3.7+ ─────
bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
rt = Router()
dp.include_router(rt)

# ───── База данных SQLite ─────
db = sqlite3.connect("trading_bot.db")
cur = db.cursor()
cur.execute(
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    project TEXT DEFAULT '',
    target REAL DEFAULT 0,
    daily_profit REAL DEFAULT 0
)
)
cur.execute(
CREATE TABLE IF NOT EXISTS trades (
    user_id INTEGER,
    date TEXT,
    profit REAL
)
)
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
