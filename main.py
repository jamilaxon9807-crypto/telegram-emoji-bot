import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import string
import time
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
bot_info = bot.get_me()
BOT_USERNAME = bot_info.username

# Foydalanuvchi holatlarini va tanlovlarini saqlash uchun
user_states = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = {} # Xotirani tozalash
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. Emoji harflar yaratish", callback_data="mode_static"))
    markup.add(InlineKeyboardButton("2. Animatsiyali harflar yaratish", callback_data="mode_animated"))
    
    bot.send_message(
        message.chat.id, 
        "Salom! J&M emoji yaratish botiga xush kelibsiz.\nKerakli funksiyani tanlang:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def handle_mode(call):
    chat_id = call.message.chat.id
    mode = call.data.split("_")[1] # static yoki animated
    
    user_states[chat_id] = {'mode': mode}
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Tanlandi: {'Emoji harflar' if mode=='static' else 'Animatsiyali harflar'}.\n\nEndi menga `.ttf` yoki `.otf` formatidagi shrift faylini yuboring."
    )

@bot.message_handler(content_types=['document'])
def handle_font(message):
    chat_id = message.chat.id
    if chat_id not in user_states or 'mode' not in user_states[chat_id]:
        bot.reply_to(message, "Iltimos, oldin /start buyrug'ini bosing va menyudan rejimni tanlang.")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        font_path = f"{chat_id}_font.ttf"
        with open(font_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        user_states[chat_id]['font'] = font_path
        bot.reply_to(message, "Shrift qabul qilindi! Endi emoji uchun kerakli HEX rang kodini yuboring (masalan: #FF0000 yoki #0000FF).")
    except Exception as e:
        bot.reply_to(message, "Xatolik: Shrift faylini yuklab bo'lmadi.")

@bot.message_handler(func=lambda message: message.chat.id in user_states and 'font' in user_states[message.chat.id] and 'color' not in user_states[message.chat.id])
def handle_color(message):
    chat_id = message.chat.id
    color = message.text.strip()
    user_states[chat_id]['color'] = color
    
    state = user_states[chat_id]
    mode = state['mode']
    font_path = state['font']

    bot.reply_to(message, f"Rang ({color}) qabul qilindi! Emojilar to'plami tayyorlanmoqda, iltimos biroz kuting...")

    pack_name = f"emoji_{chat_id}_{int(time.time())}_by_{BOT_USERNAME}"
    pack_title = "J&M Custom Emojis"
    characters = list(string.ascii_uppercase) + list(string.digits)

    try:
        font = ImageFont.truetype(font_path, 350)
    except:
        bot.reply_to(message, "Shriftni o'qishda xatolik yuz berdi. /start bosib boshtandan urinib ko'ring.")
        return

    first_sticker = True
    success_count = 0

    for char in characters:
        try:
            # 512x512 o'lchamda chizib olib, Telegram formatiga moslaymiz
            img = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            bbox = draw.textbbox((0, 0), char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (512 - text_width) / 2
            y = (512 - text_height) / 2 - bbox[1]

            draw.text((x, y), char, font=font, fill=color)

            output_path = f"{chat_id}_temp.webp"
            img.save(output_path, "WEBP")

            emoji_icon = ["✨"]

            with open(output_path, 'rb') as f:
                input_sticker = telebot.types.InputSticker(f, emoji_icon)
                
                if first_sticker:
                    bot.create_new_sticker_set(
                        user_id=message.from_user.id,
                        name=pack_name,
                        title=pack_title,
                        stickers=[input_sticker],
                        sticker_format="animated" if mode == "animated" else "static",
                        sticker_type="custom_emoji"
                    )
                    first_sticker = False
                else:
                    bot.add_sticker_to_set(
                        user_id=message.from_user.id,
                        name=pack_name,
                        sticker=input_sticker
                    )

            os.remove(output_path)
            success_count += 1
            time.sleep(0.1)
        except Exception as e:
            continue

    if success_count > 0:
        pack_url = f"https://t.me/addstickers/{pack_name}"
        bot.send_message(chat_id, f"🎉 Emojilar to'plami muvaffaqiyatli tayyor!\n\nQuyidagi ssilkaga bosib to'plamni qo'shib oling:\n{pack_url}")
    else:
        bot.send_message(chat_id, "Xatolik: Emojilarni yaratishda xatolik yuz berdi.")

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)

