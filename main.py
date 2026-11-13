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
