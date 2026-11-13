import asyncio
import time
import json
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

# ✅ Вставь сюда токен своего бота
TOKEN = "7353280157:AAEjT7duosDKOyYqmn9I8SuupsDF9JIE1mU"

# ✅ ID Telegram-группы (куда бот пересылает отзывы)
GROUP_CHAT_ID = -1002296151762

# ⚙️ Настройки
COOLDOWN_SECONDS = 3 * 24 * 60 * 60  # 3 дня
MIN_TEXT_LENGTH = 10
STORAGE_FILE = "feedback_storage.json"

# 🤖 Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

# 🧠 Память отправок
try:
    with open(STORAGE_FILE, "r") as f:
        user_last_feedback = json.load(f)
except FileNotFoundError:
    user_last_feedback = {}

def save_storage():
    with open(STORAGE_FILE, "w") as f:
        json.dump(user_last_feedback, f)

# 🟢 Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Hi! You can send me message.\n\n"
        "📨 Only text, longer than 10 characters are allowed, once every 3 days."
    )

# 📩 Обработка текстовых сообщений
@dp.message()
async def handle_feedback(message: Message):
    user_id = str(message.from_user.id)

    if message.content_type != "text":
        await message.answer("❌ Only text messages are accepted.")
        return

    if len(message.text.strip()) < MIN_TEXT_LENGTH:
        await message.answer(f"❌ Message too short. Minimum length is {MIN_TEXT_LENGTH} characters.")
        return

    now = time.time()
    last_time = user_last_feedback.get(user_id, 0)

    if now - last_time < COOLDOWN_SECONDS:
        remaining = int((COOLDOWN_SECONDS - (now - last_time)) / 3600)
        await message.answer(f"⌛ You can send again in {remaining} hours.")
        return

    username = message.from_user.username or "NoUsername"
    text = f"📩 Feedback from @{username} (ID: {user_id}):\n\n{message.text}"

    await bot.send_message(GROUP_CHAT_ID, text)
    await message.answer("✅ Thank you! Your message has been sent to the admin.")

    user_last_feedback[user_id] = now
    save_storage()

# 🚀 Точка входа
async def main():
    print("🤖 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
