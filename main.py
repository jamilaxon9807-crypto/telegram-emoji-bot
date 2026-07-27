import os
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

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
                char = chr(char_code)
                if char.isprintable() and not char.isspace():
                    chars.add(char)
        
        uppercase = sorted([c for c in chars if c.isupper()])     
        lowercase = sorted([c for c in chars if c.islower()])     
        digits = sorted([c for c in chars if c.isdigit()])        
        others = sorted([c for c in chars if not c.isupper() and not c.islower() and not c.isdigit()]) 
        
        ordered_chars = uppercase + lowercase + digits + others
        
        return ordered_chars[:200] if ordered_chars else list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()")
    except Exception:
        return list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()")

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

    status_msg = bot.reply_to(message, f"🎨 Rang (`{color}`) qabul qilindi!\n\n⚙️ Katta harflar, kichik harflar va sonlar tartib bilan tayyorlanmoqda...", parse_mode="Markdown")

    ts = int(time.time())
    pack_name = f"e_{chat_id}_{ts}_by_{BOT_USERNAME}".lower()
    pack_title = f"Custom Emojis (@{BOT_USERNAME})"
    
    characters = get_supported_chars(font_path)

    try:
        font = ImageFont.truetype(font_path, 70)
    except Exception as e:
        bot.edit_message_text(f"❌ Shrift faylida xatolik: {e}", chat_id, status_msg.message_id)
        return

    # 1. Rasm fayllarini tayyorlash
    temp_files = []
    for i, char in enumerate(characters):
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

    # Telegram limitiga ko'ra emojilarni 50 tadan "paket"larga (batch) bo'lamiz
    batches = [temp_files[i:i + 50] for i in range(0, len(temp_files), 50)]
    success_count = 0

    try:
        bot.edit_message_text(
            f"⚡ Jami **{len(temp_files)}** ta belgi topildi. Yuklanmoqda...",
            chat_id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
        
        # Birinchi paket bilan to'plamni (pack) yaratamiz
        first_batch = batches[0]
        opened_files = []
        stickers_batch1 = []
        for path, char in first_batch:
            f = open(path, 'rb')
            opened_files.append(f)
            stickers_batch1.append(InputSticker(f, ["✨"]))
            
        bot.create_new_sticker_set(
            user_id=message.from_user.id,
            name=pack_name,
            title=pack_title,
            stickers=stickers_batch1,
            sticker_format="static",
            sticker_type="custom_emoji"
        )
        success_count += len(first_batch)
        
        for f in opened_files:
            f.close()
            
        # Qolgan paketlarni qo'shamiz (add_sticker_to_set bilan)
        # Bitta-bitta so'rov tashlash Telegramni limitiga tiqmasligi uchun biroz pauza qilamiz
        for batch_index, batch in enumerate(batches[1:], start=2):
            for path, char in batch:
                attempts = 0
                while attempts < 3:
                    try:
                        with open(path, 'rb') as f:
                            st = InputSticker(f, ["✨"])
                            bot.add_sticker_to_set(
                                user_id=message.from_user.id,
                                name=pack_name,
                                sticker=st
                            )
                        success_count += 1
                        time.sleep(0.4) # Limitga tushmaslik uchun
                        break 
                    except Exception as api_err:
                        err_str = str(api_err).lower()
                        if "too many requests" in err_str or "429" in err_str:
                            time.sleep(3)
                        attempts += 1
                        
            # Xabarni yangilab turamiz
            try:
                bot.edit_message_text(
                    f"⚡ Kiritilmoqda... **{success_count}/{len(temp_files)}** ta belgi yuklandi.",
                    chat_id,
                    status_msg.message_id,
                    parse_mode="Markdown"
                )
            except:
                pass

    except Exception as e:
        bot.edit_message_text(f"❌ Telegram to'plam yaratishda xatolik berdi:\n`{e}`", chat_id, status_msg.message_id, parse_mode="Markdown")
        # Xatolikda tozalash
        for path, _ in temp_files:
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(font_path):
            os.remove(font_path)
        user_states.pop(chat_id, None)
        return

    # Barcha ishlari tugagach, tozalash
    for path, _ in temp_files:
        if os.path.exists(path):
            os.remove(path)
    if os.path.exists(font_path):
        os.remove(font_path)

    if success_count > 0:
        pack_url = f"https://t.me/addemoji/{pack_name}"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✨ Emojilar to'plamini qo'shib olish", url=pack_url))

        bot.edit_message_text(
            f"🎉 **Tabriklaymiz! Emoji to'plami tayyor!**\n\n"
            f"✅ Barcha harflar va sonlar aniq tartibda (Katta harflar -> Kichik harflar -> Sonlar -> Boshqa elementlar) yig'ilib, jami **{success_count}** ta maxsus emoji yaratildi!\n\n"
            f"🔗 **To'plam havolasi:**\n{pack_url}\n\n"
            f"👇 *Pastroqdagi tugmani bosing va to'plamni Telegram'ga qo'shib oling:*",
            chat_id, 
            status_msg.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.edit_message_text("❌ Xatolik yuz berdi, emojilarni saqlab bo'lmadi.", chat_id, status_msg.message_id)

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)
