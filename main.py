import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
import os
import time
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
BOT_USERNAME = bot.get_me().username

user_states = {}

# Shrift faylidan qaysi harf va belgilar borligini aniqlash funksiyasi
def get_supported_chars(font_path):
    try:
        ttf = TTFont(font_path)
        chars = set()
        for table in ttf['cmap'].tables:
            for char_code in table.cmap.keys():
                chars.add(chr(char_code))
        
        # Telegram bitta stiker to'plamiga 200 tagacha sig'diradi.
        # Biz eng kerakli harf, son va belgilarni ajratib olamiz.
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%&?"
        supported = [c for c in allowed_chars if c in chars]
        return supported if supported else list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    except:
        return list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = {} 
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. Emoji harflar yaratish", callback_data="mode_static"))
    markup.add(InlineKeyboardButton("2. Animatsiyali harflar yaratish", callback_data="mode_animated"))
    
    bot.send_message(
        message.chat.id, 
        "J&M Custom Emoji Botiga xush kelibsiz!\nKerakli funksiyani tanlang:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def handle_mode(call):
    chat_id = call.message.chat.id
    mode = call.data.split("_")[1]
    
    if mode == "animated":
        bot.answer_callback_query(call.id, "Animatsiyali emojilar tez kunda qo'shiladi!", show_alert=True)
        return
        
    user_states[chat_id] = {'mode': mode}
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="Emoji harflar (100x100) yaratish bo'limi.\n\nIltimos, `.ttf` yoki `.otf` formatidagi shrift faylini yuboring."
    )

@bot.message_handler(content_types=['document'])
def handle_font(message):
    chat_id = message.chat.id
    if chat_id not in user_states or 'mode' not in user_states[chat_id]:
        bot.reply_to(message, "Iltimos, /start buyrug'ini bosing va menyudan tanlang.")
        return

    bot.reply_to(message, "Shrift qabul qilinmoqda, kuting...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        font_path = f"{chat_id}_font.ttf"
        with open(font_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        user_states[chat_id]['font'] = font_path
        bot.send_message(chat_id, "✅ Shrift muvaffaqiyatli saqlandi!\n\nEndi emojilar uchun kerakli HEX rang kodini yuboring (masalan: #FF0000, #000000).")
    except Exception as e:
        bot.reply_to(message, "❌ Shriftni yuklab bo'lmadi. Boshqa fayl sinab ko'ring.")

@bot.message_handler(func=lambda message: message.chat.id in user_states and 'font' in user_states[message.chat.id] and 'color' not in user_states[message.chat.id])
def handle_color(message):
    chat_id = message.chat.id
    color = message.text.strip()
    user_states[chat_id]['color'] = color
    
    font_path = user_states[chat_id]['font']

    bot.reply_to(message, f"🎨 Rang ({color}) qabul qilindi!\n\nShrift ichidagi barcha mavjud belgilarni qidiryapman va to'plam yaratyapman (bu 1-2 daqiqa oladi)...")

    pack_name = f"custom_emojis_{chat_id}_{int(time.time())}_by_{BOT_USERNAME}"
    pack_title = "J&M Custom Emojis"
    
    # Shrift ichidagi mavjud harflarni o'qib olish
    characters = get_supported_chars(font_path)

    try:
        # Aniq 100x100 ga moslashtirish uchun shrift o'lchami ~70
        font = ImageFont.truetype(font_path, 70)
    except:
        bot.send_message(chat_id, "❌ Shriftni o'qishda xatolik yuz berdi.")
        return

    first_sticker = True
    success_count = 0

    for char in characters:
        try:
            # Qat'iy 100x100 shaffof fon
            img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # Harfni aniq markazga joylash
            bbox = draw.textbbox((0, 0), char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (100 - text_width) / 2
            y = (100 - text_height) / 2 - bbox[1]

            draw.text((x, y), char, font=font, fill=color)

            # WEBP formatida saqlash (Telegram aynan shuni talab qiladi)
            output_path = f"{chat_id}_temp.webp"
            img.save(output_path, "WEBP")

            # Harfga mos standart emoji biriktirish (masalan, A harfiga ✨)
            emoji_icon = ["✨"]

            with open(output_path, 'rb') as f:
                input_sticker = telebot.types.InputSticker(f, emoji_icon)
                
                if first_sticker:
                    # Birinchi fayl orqali to'plamni yaratish
                    bot.create_new_sticker_set(
                        user_id=message.from_user.id,
                        name=pack_name,
                        title=pack_title,
                        stickers=[input_sticker],
                        sticker_format="static",
                        sticker_type="custom_emoji"
                    )
                    first_sticker = False
                else:
                    # Qolgan fayllarni shu to'plam ustiga qo'shib borish
                    bot.add_sticker_to_set(
                        user_id=message.from_user.id,
                        name=pack_name,
                        sticker=input_sticker
                    )

            os.remove(output_path)
            success_count += 1
            time.sleep(0.1) # Telegramni qotirib qo'ymaslik uchun kichik pauza
        except Exception as e:
            continue

    if success_count > 0:
        pack_url = f"https://t.me/addstickers/{pack_name}"
        bot.send_message(chat_id, f"🎉 Ajoyib! {success_count} ta belgidan iborat 100x100 o'lchamdagi emoji to'plami tayyor.\n\nQuyidagi ssilkaga bosib, qo'shib oling:\n{pack_url}")
    else:
        bot.send_message(chat_id, "❌ Xatolik: Emojilarni yaratib bo'lmadi. Shriftda muammo bo'lishi mumkin.")

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)
