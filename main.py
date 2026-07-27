import os
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Bot username'ini avtomatik olish
try:
    BOT_USERNAME = bot.get_me().username
except Exception:
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
    except Exception:
        return list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = {} 
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. Emoji harflar yaratish", callback_data="mode_static"))
    markup.add(InlineKeyboardButton("2. Animatsiyali harflar yaratish", callback_data="mode_animated"))
    
    bot.send_message(
        message.chat.id, 
        "👋 **J&M Custom Emoji Botiga xush kelibsiz!**\n\nQuyidagi menyudan kerakli bo'limni tanlang:", 
        reply_markup=markup,
        parse_mode="Markdown"
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
        text="🔤 **Emoji harflar (100x100) yaratish bo'limi**\n\nIltimos, `.ttf` yoki `.otf` formatidagi shrift (font) faylini yuboring.",
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['document'])
def handle_font(message):
    chat_id = message.chat.id
    if chat_id not in user_states or 'mode' not in user_states[chat_id]:
        bot.reply_to(message, "Iltimos, avval /start buyrug'ini bosing va menyudan bo'limni tanlang.")
        return

    status_reply = bot.reply_to(message, "📥 Shrift fayli yuklab olinmoqda...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        font_path = f"font_{chat_id}.ttf"
        with open(font_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        user_states[chat_id]['font'] = font_path
        bot.edit_message_text(
            "✅ Shrift muvaffaqiyatli saqlandi!\n\nEndi emojilar uchun kerakli HEX rang kodini yuboring (masalan: `#FF0000` yoki `#000000`).",
            chat_id,
            status_reply.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Shriftni yuklab bo'lmadi: {e}", chat_id, status_reply.message_id)

@bot.message_handler(func=lambda message: message.chat.id in user_states and 'font' in user_states[message.chat.id] and 'color' not in user_states[message.chat.id])
def handle_color(message):
    chat_id = message.chat.id
    color = message.text.strip()
    user_states[chat_id]['color'] = color
    font_path = user_states[chat_id]['font']

    status_msg = bot.reply_to(message, f"🎨 Rang (`{color}`) qabul qilindi!\n\n⚙️ Emoji to'plami shakllantirilmoqda, biroz kuting...", parse_mode="Markdown")

    # Nom uzunligini ixchamlashtiramiz (Telegram 64 belgi limitiga sig'ishi uchun)
    short_ts = str(int(time.time()))[-5:]
    pack_name = f"e_{chat_id}_{short_ts}_by_{BOT_USERNAME}"
    pack_title = f"Custom Emojis (@{BOT_USERNAME})"
    
    characters = get_supported_chars(font_path)
    total_chars = len(characters)

    try:
        font = ImageFont.truetype(font_path, 70)
    except Exception as e:
        bot.edit_message_text(f"❌ Shrift faylida xatolik: {e}", chat_id, status_msg.message_id)
        return

    first_sticker = True
    success_count = 0
    last_edit_time = time.time()

    for i, char in enumerate(characters):
        # Telegram'ning xabarni tahrirlash limitiga tushmaslik uchun har 4 soniyada 1 marta yangilaymiz
        current_time = time.time()
        if (current_time - last_edit_time > 4.0) or (i == total_chars - 1):
            try:
                bot.edit_message_text(
                    f"🎨 Rang: `{color}`\n"
                    f"⏳ Jarayon: **{success_count}/{total_chars}** belgi tayyorlandi...\n"
                    f"<i>Bot: @{BOT_USERNAME}</i>",
                    chat_id, 
                    status_msg.message_id,
                    parse_mode="HTML"
                )
                last_edit_time = current_time
            except Exception:
                pass

        output_path = f"temp_{chat_id}.webp"
        try:
            img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            bbox = draw.textbbox((0, 0), char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (100 - text_width) / 2
            y = (100 - text_height) / 2 - bbox[1]

            draw.text((x, y), char, font=font, fill=color)
            img.save(output_path, "WEBP")
        except Exception:
            continue

        attempts = 0
        uploaded = False
        while not uploaded and attempts < 3:
            try:
                with open(output_path, 'rb') as f:
                    input_sticker = InputSticker(f, ["✨"])
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
                    else:
                        bot.add_sticker_to_set(
                            user_id=message.from_user.id,
                            name=pack_name,
                            sticker=input_sticker
                        )
                uploaded = True
                success_count += 1
                time.sleep(0.3)
            except Exception as api_err:
                err_str = str(api_err).lower()
                attempts += 1
                if "too many requests" in err_str or "429" in err_str:
                    time.sleep(5)
                else:
                    time.sleep(1)

        if os.path.exists(output_path):
            os.remove(output_path)

    if os.path.exists(font_path):
        os.remove(font_path)

    if success_count > 0:
        pack_url = f"https://t.me/addstickers/{pack_name}"
        bot.edit_message_text(
            f"🎉 **Emoji to'plami muvaffaqiyatli yaratildi!**\n\n"
            f"✨ Jami **{success_count}** ta belgi tayyorlandi.\n\n"
            f"🔗 **To'plamni qo'shib olish uchun ssilka:**\n{pack_url}\n\n"
            f"🤖 *Bot: @{BOT_USERNAME}*",
            chat_id, 
            status_msg.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.edit_message_text(
            "❌ **Xatolik:** Birorta ham emoji yaratib bo'lmadi.\nIltimos, qaytadan /start bosib sinab ko'ring.", 
            chat_id, 
            status_msg.message_id,
            parse_mode="Markdown"
        )

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)
