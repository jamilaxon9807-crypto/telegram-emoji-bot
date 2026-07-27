import os
import time
import math
import numpy as np
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from PIL import Image, ImageDraw, ImageFont
import imageio

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

try:
    BOT_USERNAME = bot.get_me().username
except Exception:
    BOT_USERNAME = "JM_CreatorStudio_bot"

user_states = {}

ENG_UPPER = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ENG_LOWER = list("abcdefghijklmnopqrstuvwxyz")
RU_UPPER = list("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
RU_LOWER = list("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
DIGITS = list("1234567890")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = {} 
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. Statik emoji harflar", callback_data="mode_static"))
    markup.add(InlineKeyboardButton("2. 🎬 Animatsiyali emoji harflar", callback_data="mode_animated"))
    
    bot.send_message(
        message.chat.id, 
        "👋 <b>J&M Custom Emoji Botiga xush kelibsiz!</b>\n\nQuyidagi menyudan kerakli rejimni tanlang:", 
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def handle_mode(call):
    chat_id = call.message.chat.id
    mode = call.data.split("_")[1]
    
    user_states[chat_id] = {'mode': mode, 'step': 'await_font'}
    bot.answer_callback_query(call.id)
    
    mode_title = "🎬 Animatsiyali" if mode == "animated" else "🔤 Statik"
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"{mode_title} <b>emoji yaratish (1-BOSQICH)</b>\n\nIltimos, <code>.ttf</code> yoki <code>.otf</code> formatidagi shrift faylini yuboring.",
        parse_mode="HTML"
    )

@bot.message_handler(content_types=['document'])
def handle_font(message):
    chat_id = message.chat.id
    if chat_id not in user_states or user_states[chat_id].get('step') != 'await_font':
        bot.reply_to(message, "Iltimos, avval /start buyrug'ini bosing va jarayonni boshlang.")
        return

    status_reply = bot.reply_to(message, "📥 Shrift fayli yuklab olinmoqda...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        font_path = f"font_{chat_id}.ttf"
        with open(font_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        user_states[chat_id]['font'] = font_path
        user_states[chat_id]['step'] = 'await_lang'

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🇬🇧 ENG (Ingliz)", callback_data="lang_eng"),
            InlineKeyboardButton("🇷🇺 RU (Rus)", callback_data="lang_ru")
        )

        bot.edit_message_text(
            "🌐 <b>2-BOSQICH: Tilni tanlang</b>\n\nEmojilar qaysi alifbo asosida yaratilsin?",
            chat_id,
            status_reply.message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Shriftni yuklab bo'lmadi: {e}", chat_id, status_reply.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def handle_lang(call):
    chat_id = call.message.chat.id
    lang = call.data.split("_")[1]
    user_states[chat_id]['lang'] = lang
    user_states[chat_id]['step'] = 'await_color'
    
    bot.answer_callback_query(call.id)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎨 Telegram Adaptive", callback_data="color_adaptive"))

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="🎨 <b>3-BOSQICH: Rangni belgilang</b>\n\nHEX rang kodini yuboring (masalan: <code>#FF0000</code> yoki <code>#0088CC</code>)\nyoki pastdagi <b>Telegram Adaptive</b> tugmasini bosing:",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "color_adaptive")
def handle_color_adaptive(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    process_color_selection(chat_id, call.message.message_id, "#000000")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get('step') == 'await_color')
def handle_color_text(message):
    chat_id = message.chat.id
    color = message.text.strip()
    status_msg = bot.reply_to(message, "🎨 Rang qabul qilindi...")
    process_color_selection(chat_id, status_msg.message_id, color)

def process_color_selection(chat_id, message_id, color):
    user_states[chat_id]['color'] = color
    user_states[chat_id]['step'] = 'await_case'

    markup = InlineKeyboardMarkup()
    lang = user_states[chat_id]['lang']
    
    if lang == 'eng':
        markup.add(InlineKeyboardButton("🔠 Katta harflar (A-Z) + Sonlar", callback_data="case_upper"))
        markup.add(InlineKeyboardButton("🔡 Kichik harflar (a-z) + Sonlar", callback_data="case_lower"))
    else:
        markup.add(InlineKeyboardButton("🔠 Katta harflar (А-Я) + Sonlar", callback_data="case_upper"))
        markup.add(InlineKeyboardButton("🔡 Kichik harflar (а-я) + Sonlar", callback_data="case_lower"))

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="🔤 <b>4-BOSQICH: Harflar shaklini tanlang</b>\n\nKerakli variantni tanlang:",
        reply_markup=markup,
        parse_mode="HTML"
    )

def create_animated_webm(char, font_path, color, is_digit, output_path):
    """Kadrba-kadr pulsatsiyalanuvchi WEBM video (animatsiya) yaratish"""
    frames = []
    total_frames = 16  # Silliq va tezkor sikl uchun 16 kadr
    
    for f_idx in range(total_frames):
        # Silliq kattalashib-kichiklashuv katsenti (sine wave)
        scale = 0.82 + 0.18 * math.sin(2 * math.pi * f_idx / total_frames)
        
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if is_digit:
            font_size = int(45 * scale)
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            # Doiraning o'lchami ham harakatlanadi
            r_margin = int(8 + (1 - scale) * 10)
            draw.ellipse((r_margin, r_margin, 100 - r_margin, 100 - r_margin), outline=color, width=4)
            
            bbox = draw.textbbox((0, 0), char, font=font)
            x = (100 - (bbox[2] - bbox[0])) / 2
            y = (100 - (bbox[3] - bbox[1])) / 2 - bbox[1]
            draw.text((x, y), char, font=font, fill=color)
        else:
            font_size = int(65 * scale)
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
                
            bbox = draw.textbbox((0, 0), char, font=font)
            x = (100 - (bbox[2] - bbox[0])) / 2
            y = (100 - (bbox[3] - bbox[1])) / 2 - bbox[1]
            draw.text((x, y), char, font=font, fill=color)

        frames.append(np.array(img))

    # Transparent WEBM VP9 video ko'rinishida saqlash
    imageio.mimsave(
        output_path, 
        frames, 
        fps=20, 
        codec='libvpx-vp9', 
        pixelformat='yuva420p',
        output_params=['-auto-alt-ref', '0']
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("case_"))
def handle_case_and_generate(call):
    chat_id = call.message.chat.id
    case_type = call.data.split("_")[1]
    bot.answer_callback_query(call.id)

    font_path = user_states[chat_id]['font']
    lang = user_states[chat_id]['lang']
    color = user_states[chat_id]['color']
    mode = user_states[chat_id].get('mode', 'static')

    if lang == 'eng':
        letters = ENG_UPPER if case_type == 'upper' else ENG_LOWER
    else:
        letters = RU_UPPER if case_type == 'upper' else RU_LOWER

    target_chars = letters + DIGITS

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"⚡ <b>Jami {len(target_chars)} ta {'animatsiyali' if mode == 'animated' else 'statik'} emoji tayyorlanmoqda...</b>\n\n<i>Iltimos, kuting (bu biroz vaqt olishi mumkin)...</i>",
        parse_mode="HTML"
    )

    ts = int(time.time())
    pack_name = f"e_{chat_id}_{ts}_by_{BOT_USERNAME}".lower()
    pack_title = f"Custom Emojis (@{BOT_USERNAME})"

    temp_files = []
    
    for i, char in enumerate(target_chars):
        if mode == 'animated':
            ext = "webm"
            img_path = f"temp_{chat_id}_{i}.webm"
            try:
                create_animated_webm(char, font_path, color, char.isdigit(), img_path)
                temp_files.append(img_path)
            except Exception as ex:
                continue
        else:
            ext = "webp"
            img_path = f"temp_{chat_id}_{i}.webp"
            try:
                font_letters = ImageFont.truetype(font_path, 65)
                font_digits = ImageFont.truetype(font_path, 45)
                
                img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
                draw = ImageDraw.Draw(img)

                if char.isdigit():
                    draw.ellipse((8, 8, 92, 92), outline=color, width=4)
                    bbox = draw.textbbox((0, 0), char, font=font_digits)
                    x = (100 - (bbox[2] - bbox[0])) / 2
                    y = (100 - (bbox[3] - bbox[1])) / 2 - bbox[1]
                    draw.text((x, y), char, font=font_digits, fill=color)
                else:
                    bbox = draw.textbbox((0, 0), char, font=font_letters)
                    x = (100 - (bbox[2] - bbox[0])) / 2
                    y = (100 - (bbox[3] - bbox[1])) / 2 - bbox[1]
                    draw.text((x, y), char, font=font_letters, fill=color)

                img.save(img_path, "WEBP")
                temp_files.append(img_path)
            except Exception:
                continue

    if not temp_files:
        bot.edit_message_text("❌ Emojilarni yaratishda xatolik yuz berdi.", chat_id, call.message.message_id)
        if os.path.exists(font_path):
            os.remove(font_path)
        return

    # Telegram'ga stiker to'plami sifatida joylash
    opened_files = []
    stickers = []
    for path in temp_files:
        f = open(path, 'rb')
        opened_files.append(f)
        stickers.append(InputSticker(f, ["✨"]))

    sticker_format_type = "video" if mode == "animated" else "static"

    try:
        bot.create_new_sticker_set(
            user_id=call.from_user.id,
            name=pack_name,
            title=pack_title,
            stickers=stickers,
            sticker_format=sticker_format_type,
            sticker_type="custom_emoji"
        )
        
        for f in opened_files:
            f.close()

        pack_url = f"https://t.me/addemoji/{pack_name}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✨ {len(temp_files)} ta emojini qo'shib olish", url=pack_url))

        bot.edit_message_text(
            f"🎉 <b>Tabriklaymiz! {'Animatsiyali' if mode == 'animated' else 'Statik'} emoji to'plami tayyor!</b>\n\n"
            f"✅ Roppa-rosa <b>{len(temp_files)}</b> ta emoji to'liq yaratildi!\n\n"
            f"🔗 <b>To'plam havolasi:</b>\n{pack_url}\n\n"
            f"👇 <i>Pastroqdagi tugmani bosing va to'plamni Telegram'ga qo'shib oling:</i>",
            chat_id, 
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )

    except Exception as e:
        bot.edit_message_text(f"❌ Telegram to'plam yaratishda xatolik berdi:\n<code>{e}</code>", chat_id, call.message.message_id, parse_mode="HTML")
        for f in opened_files:
            f.close()

    for path in temp_files:
        if os.path.exists(path):
            os.remove(path)
    if os.path.exists(font_path):
        os.remove(font_path)

    user_states.pop(chat_id, None)

bot.polling(none_stop=True)
