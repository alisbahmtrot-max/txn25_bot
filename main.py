import telebot
from telebot import types
import yt_dlp
import os

# التوكن الخاص بك
API_TOKEN = '8330959344:AAFav6IQ1EdM1o_ePZilYsUKrskTESlaS1I'
bot = telebot.TeleBot(API_TOKEN)

# تخزين مؤقت لخيارات المستخدم
user_storage = {}

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "مرحباً بك! أرسل لي رابط قائمة تشغيل يوتيوب وسأقوم بتحميلها لك.")

@bot.message_handler(func=lambda m: 'list=' in m.text or 'playlist' in m.text)
def ask_all_or_single(message):
    user_storage[message.chat.id] = {'url': message.text}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("الكل", callback_data="mode_all"),
               types.InlineKeyboardButton("فيديو واحد فقط", callback_data="mode_single"))
    bot.send_message(message.chat.id, "هل تريد تحميل القائمة كاملة أم فيديو واحد؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def ask_format(call):
    user_storage[call.message.chat.id]['mode'] = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("صوت (MP3)", callback_data="form_audio"),
               types.InlineKeyboardButton("فيديو (MP4)", callback_data="form_video"))
    bot.edit_message_text("اختر الصيغة المطلوبة:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'form_video')
def ask_quality(call):
    markup = types.InlineKeyboardMarkup()
    # خيارات الجودة
    markup.add(types.InlineKeyboardButton("360p", callback_data="qual_360"),
               types.InlineKeyboardButton("720p", callback_data="qual_720"),
               types.InlineKeyboardButton("أعلى جودة متاحة", callback_data="qual_best"))
    bot.edit_message_text("اختر دقة الفيديو:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('form_audio') or call.data.startswith('qual_'))
def process_download(call):
    chat_id = call.message.chat.id
    data = user_storage.get(chat_id)
    
    if not data:
        bot.send_message(chat_id, "حدث خطأ، يرجى إرسال الرابط مرة أخرى.")
        return

    # تحديد الجودة والصيغة
    if call.data == 'form_audio':
        format_str = 'bestaudio/best'
        ext = 'mp3'
    else:
        quality = call.data.split('_')[1]
        ext = 'mp4'
        if quality == 'best':
            format_str = 'bestvideo+bestaudio/best'
        else:
            format_str = f'bestvideo[height<={quality}]+bestaudio/best[ext=m4a]/best'

    bot.edit_message_text("جاري البدء في التحميل... يرجى الانتظار ⏳", chat_id, call.message.message_id)

    ydl_opts = {
        'format': format_str,
        'noplaylist': True if data['mode'] == 'single' else False,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    if ext == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(data['url'], download=True)
            entries = info.get('entries', [info])
            
            for entry in entries:
                filename = ydl.prepare_filename(entry)
                if ext == 'mp3': filename = filename.rsplit('.', 1)[0] + '.mp3'
                
                with open(filename, 'rb') as f:
                    if ext == 'mp3':
                        bot.send_audio(chat_id, f, caption=entry.get('title'))
                    else:
                        bot.send_video(chat_id, f, caption=entry.get('title'))
                os.remove(filename) # مسح الملف لتوفير مساحة السيرفر

        bot.send_message(chat_id, "✅ اكتمل التحميل والرفع بنجاح!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ: {str(e)}")

bot.polling()
              
