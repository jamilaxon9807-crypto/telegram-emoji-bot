import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

# Tokenni xavfsiz tarzda server muhitidan olamiz
TOKEN = os.getenv("8492254585:AAGfMZIjeq38B90rOukgwZha8618pXAob9I")

class EmojiBotStates(StatesGroup):
  waiting_for_font = State()
  waiting_for_emoji = State()
  waiting_for_color = State()

dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
  await state.clear()
  await message.answer(
      "Salom! Shriftlardan rangli Telegram WebP emojilarini yasovchi botga"
      " xush kelibsiz.\n\nIltimos, avval .ttf yoki .otf formatidagi shrift"
      " faylini yuboring:"
  )
  await state.set_state(EmojiBotStates.waiting_for_font)

@dp.message(EmojiBotStates.waiting_for_font, F.document)
async def process_font(message: Message, state: FSMContext):
  document = message.document
  if not document.file_name.endswith((".ttf", ".otf")):
    await message.answer(
        "Iltimos, faqat .ttf yoki .otf formatidagi shrift faylini yuboring!"
    )
    return

  await state.update_data(font_file_id=document.file_id)

  await message.answer(
      "Shrift qabul qilindi! ✅\n\nEndi rasmga aylantirmoqchi bo'lgan"
      " **Unicode emojilarni** yuboring (masalan: 😀, 🔥, 🚀):"
  )
  await state.set_state(EmojiBotStates.waiting_for_emoji)

@dp.message(EmojiBotStates.waiting_for_font)
async def process_font_invalid(message: Message):
  await message.answer(
      "Iltimos, hujjat ko'rinishida shrift faylini yuboring (.ttf yoki .otf)."
  )

@dp.message(EmojiBotStates.waiting_for_emoji)
async def process_emoji(message: Message, state: FSMContext):
  emojis = message.text
  await state.update_data(target_emojis=emojis)

  await message.answer(
      f"Tanlangan emojilar: {emojis} ✅\n\nEndi emoji rangini kiriting (**HEX"
      " formatida**, masalan: `#FF5733`):"
  )
  await state.set_state(EmojiBotStates.waiting_for_color)

@dp.message(EmojiBotStates.waiting_for_color)
async def process_color(message: Message, state: FSMContext):
  hex_color = message.text

  if not hex_color.startswith("#") or len(hex_color) not in (4, 7):
    await message.answer(
        "Noto'g'ri HEX format! Iltimos, masalan `#FF0000` ko'rinishida yuboring."
    )
    return

  data = await state.get_data()
  font_file_id = data.get("font_file_id")
  target_emojis = data.get("target_emojis")

  await message.answer(
      "Ma'lumotlar qabul qilindi! 🎨\n\n• Shrift ID:"
      f" {font_file_id}\n• Emojilar: {target_emojis}\n• Rang:"
      f" {hex_color}\n\n⏳ Emojilar tayyorlanmoqda va ZIP qilib yuboriladi..."
  )

  await state.clear()

async def main():
  bot = Bot(token=TOKEN)
  await dp.start_polling(bot)

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())
