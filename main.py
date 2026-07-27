import os
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

try:
    BOT_USERNAME = bot.get_me().username
except Exception:
    BOT_USERNAME = "JM_CreatorStudio_bot"

user_states = {}

# Barcha kerakli 62 ta belgi (Katta harflar, Kichik harflar va Raqamlar)
TARGET_CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = {} 
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. Emoji harflar yaratish", callback_data="mode_static"))
    markup.add(InlineKeyboardButton("2. Animatsiyali harflar yaratish", callback_data="mode_animated"))
    
    bot.send_message(
        message.chat.id, 
        "👋 <b>J&M Custom Emoji Botiga xush kelibsiz!</b>\n\nQuyidagi menyudan kerakli bo'limni tanlang:", 
        reply_markup=markup,
        parse_mode="HTML"
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
        text="🔤 <b>Emoji harflar (100x100) yaratish bo'limi</b>\n\nIltimos, <code>.ttf</code> yoki <code>.otf</code> formatidagi shrift (font) faylini yuboring.",
        parse_mode="HTML"
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
            "✅ Shrift muvaffaqiyatli saqlandi!\n\nEndi emojilar uchun kerakli HEX rang kodini yuboring (masalan: <code>#FF0000</code> yoki <code>#000000</code>).",
            chat_id,
            status_reply.message_id,
            parse_mode="HTML"
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Shriftni yuklab bo'lmadi: {e}", chat_id, status_reply.message_id)

@bot.message_handler(func=lambda message: message.chat.id in user_states and 'font' in user_states[message.chat.id] and 'color' not in user_states[message.chat.id])
def handle_color(message):
    chat_id = message.chat.id
    color = message.text.strip()
    user_states[chat_id]['color'] = color
    font_path = user_states[chat_id]['font']

    status_msg = bot.reply_to(message, f"🎨 Rang (<code>{color}</code>) qabul qilindi!\n\n⚙️ Barcha harflar va sonlar (62 ta emoji) tayyorlanmoqda...", parse_mode="HTML")

    ts = int(time.time())
    pack_name = f"e_{chat_id}_{ts}_by_{BOT_USERNAME}".lower()
    pack_title = f"Custom Emojis (@{BOT_USERNAME})"
    
    try:
        font = ImageFont.truetype(font_path, 70)
    except Exception as e:
        bot.edit_message_text(f"❌ Shrift faylida xatolik: {e}", chat_id, status_msg.message_id)
        return

    # 1. Barcha 62 ta emojini tayyorlash
    temp_files = []
    for i, char in enumerate(TARGET_CHARS):
        img_path = f"temp_{chat_id}_{i}.webp"
        try:
            img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            bbox = draw.textbbox((0, 0), char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (100 - text_width) / 2
            y = (100 - text_height) / 2 - bbox[1]

            draw.text((x, y), char, font=font, fill=color)
            img.save(img_path, "WEBP")
            temp_files.append((img_path, char))
        except Exception:
            continue

    if not temp_files:
        bot.edit_message_text("❌ Rasmlarni tayyorlashda xatolik yuz berdi.", chat_id, status_msg.message_id)
        if os.path.exists(font_path):
            os.remove(font_path)
        return

    # Telegram limitiga ko'ra emojilarni 50 ta va qolganlariga bo'lamiz
    batch1 = temp_files[:50]
    batch2 = temp_files[50:]

    opened_files_1 = []
    stickers_batch1 = []
    
    for path, char in batch1:
        f = open(path, 'rb')
        opened_files_1.append(f)
        stickers_batch1.append(InputSticker(f, ["✨"]))

    success_count = 0

    try:
        # Dastlabki 50 tasini bitta so'rovda yaratish
        bot.create_new_sticker_set(
            user_id=message.from_user.id,
            name=pack_name,
            title=pack_title,
            stickers=stickers_batch1,
            sticker_format="static",
            sticker_type="custom_emoji"
        )
        success_count += len(batch1)
        
        for f in opened_files_1:
            f.close()
            
        # Telegram serverida to'plam to'liq ro'yxatdan o'tishi uchun 2.5 soniya kutiladi
        time.sleep(2.5)

        # Qolgan barcha emojilarni (51-dan boshlab) ketma-ket birma-bir qo'shib chiqamiz
        if batch2:
            for path, char in batch2:
                for attempt in range(3):
                    try:
                        with open(path, 'rb') as f:
                            st = InputSticker(f, ["✨"])
                            bot.add_sticker_to_set(
                                user_id=message.from_user.id,
                                name=pack_name,
                                sticker=st
                            )
                        success_count += 1
                        time.sleep(0.4)
                        break
                    except Exception:
                        time.sleep(1.5)

    except Exception as e:
        bot.edit_message_text(f"❌ Telegram to'plam yaratishda xatolik berdi:\n<code>{e}</code>", chat_id, status_msg.message_id, parse_mode="HTML")
        for f in opened_files_1:
            f.close()
        for path, _ in temp_files:
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(font_path):
            os.remove(font_path)
        user_states.pop(chat_id, None)
        return

    # Fayllarni tozalash
    for path, _ in temp_files:
        if os.path.exists(path):
            os.remove(path)
    if os.path.exists(font_path):
        os.remove(font_path)

    # HTML formatida xatosiz havola va tugma
    if success_count > 0:
        pack_url = f"https://t.me/addemoji/{pack_name}"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✨ {success_count} ta emojini qo'shish", url=pack_url))

        bot.edit_message_text(
            f"🎉 <b>Tabriklaymiz! Emoji to'plami tayyor!</b>\n\n"
            f"✅ Barcha harflar va sonlar (Katta harflar, Kichik harflar va Raqamlar) yig'ilib, jami <b>{success_count}</b> ta emoji to'liq yaratildi!\n\n"
            f"🔗 <b>To'plam havolasi:</b>\n{pack_url}\n\n"
            f"👇 <i>Pastroqdagi tugmani bosing va to'plamni Telegram'ga qo'shib oling:</i>",
            chat_id, 
            status_msg.message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        bot.edit_message_text("❌ Xatolik yuz berdi, emojilarni saqlab bo'lmadi.", chat_id, status_msg.message_id)

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)
