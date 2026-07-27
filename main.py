import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
import os
import time
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
BOT_USERNAME = "JM_CreatorStudio_bot" 

user_states = {}

def get_supported_chars(font_path):
    try:
        ttf = TTFont(font_path)
        chars = set()
        for table in ttf['cmap'].tables:
            for char_code in table.cmap.keys():
                chars.add(chr(char_code))
        
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

    bot.reply_to(message, "📁 Shrift qabul qilinmoqda...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        font_path = f"{chat_id}_font.ttf"
        with open(font_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        user_states[chat_id]['font'] = font_path
        bot.send_message(chat_id, "✅ Shrift muvaffaqiyatli saqlandi!\n\nEndi emojilar uchun kerakli rang kodini yuboring (masalan: `#FF0000` yoki `#000000`).")
    except Exception as e:
        bot.reply_to(message, "❌ Shriftni yuklab bo'lmadi. Boshqa fayl sinab ko'ring.")

@bot.message_handler(func=lambda message: message.chat.id in user_states and 'font' in user_states[message.chat.id] and 'color' not in user_states[message.chat.id])
def handle_color(message):
    chat_id = message.chat.id
    color = message.text.strip()
    user_states[chat_id]['color'] = color
    font_path = user_states[chat_id]['font']

    status_msg = bot.reply_to(message, f"🎨 Rang (`{color}`) qabul qilindi!\n\n⏳ Emojilar tayyorlanmoqda, iltimos kuting...", parse_mode="Markdown")

    pack_name = f"emojis_{chat_id}_{int(time.time())}_by_jm"
    pack_title = f"Custom Emojis by @{BOT_USERNAME}"
    
    characters = get_supported_chars(font_path)
    total_chars = len(characters)

    try:
        font = ImageFont.truetype(font_path, 70)
    except:
        bot.edit_message_text("❌ Shriftni o'qishda xatolik yuz berdi.", chat_id, status_msg.message_id)
        return

    first_sticker = True
    success_count = 0

    for i, char in enumerate(characters):
        try:
            # Foiz yoki animatsiya qotib qolmasligi uchun uni har 3 harfda bir marta yangilaymiz
            if i % 3 == 0:
                try:
                    bot.edit_message_text(
                        f"🎨 Rang (`{color}`) qabul qilindi!\n\n"
                        f"⚡ Ishlov berilmoqda: <b>{success_count}/{total_chars}</b> ta belgi yuklandi...\n"
                        f"<i>Bot: @{BOT_USERNAME}</i>",
                        chat_id, 
                        status_msg.message_id,
                        parse_mode="HTML"
                    )
                except:
                    pass

            img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            bbox = draw.textbbox((0, 0), char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (100 - text_width) / 2
            y = (100 - text_height) / 2 - bbox[1]

            draw.text((x, y), char, font=font, fill=color)

            output_path = f"{chat_id}_temp.webp"
            img.save(output_path, "WEBP")
            emoji_icon = ["✨"]

            with open(output_path, 'rb') as f:
                input_sticker = telebot.types.InputSticker(f, emoji_icon)
                
                success = False
                attempts = 0
                
                # Mana shu tsikl orqali xato bersa qaytadan urinib ko'ramiz
                while not success and attempts < 5:
                    try:
                        if first_sticker:
                            bot.create_new_sticker_set(
                                user_id=message.from_user.id,
                                name=pack_name,
                                title=pack_title,
                                stickers=[input_sticker],
                                sticker_format="static",
                                sticker_type="custom_emoji"
                            )
                            first_sticker = False
                            time.sleep(1.5)
                        else:
                            bot.add_sticker_to_set(
                                user_id=message.from_user.id,
                                name=pack_name,
                                sticker=input_sticker
                            )
                            time.sleep(0.4)
                        success = True
                        success_count += 1
                    except Exception as e:
                        error_msg = str(e).lower()
                        
                        # Agar Telegram spam sifatida ko'rsa
                        if "429" in error_msg or "too many requests" in error_msg:
                            try:
                                bot.edit_message_text(
                                    f"⚠️ <b>Telegram Anti-spam tizimi sezildi!</b>\n\n"
                                    f"⏳ Botingiz limitga tushmasligi uchun avtomatik 12 soniya dam olmoqda, shundan so'ng davom etadi...\n"
                                    f"<i>Hozirgacha saqlandi: {success_count}/{total_chars}</i>",
                                    chat_id, status_msg.message_id, parse_mode="HTML"
                                )
                            except:
                                pass
                            time.sleep(12)  # Bu muhim pauza
                            attempts += 1
                        else:
                            break

            os.remove(output_path)

        except Exception as e:
            continue

    if success_count > 0:
        pack_url = f"https://t.me/addstickers/{pack_name}"
        bot.edit_message_text(
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"✨ <b>{success_count}</b> ta belgidan iborat to'liq emoji to'plami tayyor!\n\n"
            f"👉 To'plamni qo'shib olish uchun quyidagi ssilkaga bosing:\n{pack_url}\n\n"
            f"<i>Yaratuvchi: @{BOT_USERNAME}</i>",
            chat_id, 
            status_msg.message_id,
            parse_mode="HTML"
        )
    else:
        bot.edit_message_text("❌ Xatolik: Emojilarni yaratib bo'lmadi.", chat_id, status_msg.message_id)

    if os.path.exists(font_path):
        os.remove(font_path)

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)
