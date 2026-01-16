import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# =====================
# SOZLAMALAR
# =====================
TOKEN = "8439973908:AAELXx5bD5HaEy3VuJC9jTroaMbK2WGp69E"
ADMIN_ID = 5675022855  # <-- o'zingning Telegram ID ni yoz

CHANNELS = [
    {"title": "1 - kanal", "username": "@yangikinolar_Bizda", "url": "https://t.me/yangikinolar_Bizda"},
    {"title": "2 - kanal", "username": "@kinolarN1_bizda", "url": "https://t.me/kinolarN1_bizda"},
]

MOVIES_FILE = "../movies.json"

# =====================
# BOT
# =====================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =====================
# JSON bazani o‘qish/yozish
# =====================
def load_movies() -> dict:
    if not os.path.exists(MOVIES_FILE):
        with open(MOVIES_FILE, "w", encoding="utf-8") as f:
            f.write("{}")
    with open(MOVIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_movies(data: dict):
    with open(MOVIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =====================
# Obuna bo‘lmagan kanallarni topish
# =====================
async def get_unsubscribed(user_id: int):
    missing = []
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch["username"], user_id)
            if member.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return missing

def subscribe_keyboard(channels):
    rows = []
    for ch in channels:
        rows.append([types.InlineKeyboardButton(text=ch["title"], url=ch["url"])])
    rows.append([types.InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)

# =====================
# FSM: admin add
# =====================
class AddMovie(StatesGroup):
    code = State()
    wait_video = State()
    caption = State()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# =====================
# /start
# =====================
@dp.message(CommandStart())
async def start(message: types.Message):
    missing = await get_unsubscribed(message.from_user.id)
    if missing:
        await message.answer(
            "⚠️ Botdan foydalanish uchun iltimos quyidagi kanallarga obuna bo‘ling‼️",
            reply_markup=subscribe_keyboard(missing)
        )
        return
    await message.answer("✅ Obuna tasdiqlandi!\n🎬 Kino kodini yuboring:")

# =====================
# Tekshirish
# =====================
@dp.callback_query(lambda c: c.data == "check_sub")
async def check(call: types.CallbackQuery):
    missing = await get_unsubscribed(call.from_user.id)

    if not missing:
        await call.message.edit_text("✅ Obuna tasdiqlandi!\n🎬 Kino kodini yuboring:")
        await call.answer()
    else:
        await call.message.edit_reply_markup(reply_markup=subscribe_keyboard(missing))
        await call.answer("❌ Hali hamma kanalga obuna bo‘lmagansiz!", show_alert=True)

# =====================
# ADMIN: /add
# =====================
@dp.message(Command("add"))
async def add_cmd(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Siz admin emassiz.")
    await state.set_state(AddMovie.code)
    await message.answer("✅ Kino kodini kiriting (masalan: 927):")

@dp.message(AddMovie.code)
async def add_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if not code.isdigit():
        return await message.answer("❌ Kod faqat raqam bo‘lsin. Masalan: 927")
    await state.update_data(code=code)
    await state.set_state(AddMovie.wait_video)
    await message.answer("🎥 Endi kinoni video qilib yuboring (Telegram video):")

@dp.message(AddMovie.wait_video)
async def add_video(message: types.Message, state: FSMContext):
    if not message.video:
        return await message.answer("❌ Video yuboring (Document emas).")
    await state.update_data(video_id=message.video.file_id)
    await state.set_state(AddMovie.caption)
    await message.answer("📝 Caption yozing (yoki '-' deb yuboring):")

@dp.message(AddMovie.caption)
async def add_caption(message: types.Message, state: FSMContext):
    data = await state.get_data()
    code = data["code"]
    video_id = data["video_id"]
    caption = message.text.strip()
    if caption == "-":
        caption = ""

    movies = load_movies()
    movies[code] = {"video": video_id, "caption": caption, "views": 0}
    save_movies(movies)

    await state.clear()
    await message.answer(f"✅ Saqlandi!\nKino kodi: {code}")

# =====================
# ADMIN: /del 927
# =====================
@dp.message(Command("del"))
async def del_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Siz admin emassiz.")
    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("❗ Foydalanish: /del 927")

    code = parts[1].strip()
    movies = load_movies()
    if code not in movies:
        return await message.answer("❌ Bunday kod yo‘q.")
    movies.pop(code)
    save_movies(movies)
    await message.answer(f"✅ O‘chirildi: {code}")

# =====================
# ADMIN: /list
# =====================
@dp.message(Command("list"))
async def list_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Siz admin emassiz.")
    movies = load_movies()
    if not movies:
        return await message.answer("📭 Hozircha kino yo‘q.")
    text = "🎬 Kino ro‘yxati:\n\n"
    for code, info in movies.items():
        text += f"✅ {code} — views: {info.get('views', 0)}\n"
    await message.answer(text)

# =====================
# KINO KOD QABUL QILISH
# =====================
@dp.message()
async def movie_handler(message: types.Message):
    # avval obuna tekshiramiz
    missing = await get_unsubscribed(message.from_user.id)
    if missing:
        await message.answer("⚠️ Avval kanallarga obuna bo‘ling!", reply_markup=subscribe_keyboard(missing))
        return

    code = message.text.strip()
    movies = load_movies()

    if code in movies:
        movies[code]["views"] = int(movies[code].get("views", 0)) + 1
        save_movies(movies)

        await message.answer_video(
            video=movies[code]["video"],
            caption=movies[code].get("caption", "")
        )
    else:
        await message.answer("❌ Bunday kino topilmadi")

# =====================
# RUN
# =====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
