import telebot
from telebot import types
import subprocess
import os
from static_ffmpeg import add_paths

# إضافة مسار ffmpeg تلقائياً لبيئة العمل
add_paths()

# التوكن الخاص بك
API_TOKEN = '8532448939:AAHt3VRMnROqmemsvFbWsTjpapRotelbOng'
bot = telebot.TeleBot(API_TOKEN)

# تخزين بيانات المستخدمين المؤقتة والعمليات الجارية
user_data = {}
active_processes = [] 

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_data[user_id] = {'step': 'WAITING_KEY'}
    bot.reply_to(message, "مرحباً بك في بوت البث المتقدم! 🎥\n\nمن فضلك أرسل **Stream Key** الخاص بفيسبوك الآن:")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    state = user_data.get(user_id, {}).get('step')

    # المرحلة الأولى: استلام الـ Key
    if state == 'WAITING_KEY':
        user_data[user_id]['key'] = message.text
        user_data[user_id]['step'] = 'WAITING_LINK'
        bot.reply_to(message, "✅ تم حفظ المفتاح.\n\nالآن من فضلك أرسل رابط **m3u8** الذي تريد بثه:")

    # المرحلة الثانية: استلام الرابط وتشغيل البث
    elif state == 'WAITING_LINK':
        m3u8_url = message.text
        stream_key = user_data[user_id]['key']
        user_data[user_id]['step'] = None 
        
        bot.reply_to(message, "⏳ جارٍ تشغيل البث... سيتم إخطارك عند البدء.")

        # عنوان فيسبوك RTMP
        rtmp_url = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"
        
        # أمر FFmpeg الاحترافي (معدل ليعمل مع المسار المحمول)
        ffmpeg_cmd = [
            'ffmpeg', 
            '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
            '-re', '-i', m3u8_url,
            '-c:v', 'copy', '-c:a', 'aac', '-ar', '44100', '-ab', '128k',
            '-f', 'flv', rtmp_url
        ]

        try:
            # تشغيل العملية وتجاهل المخرجات الضخمة لتوفير الذاكرة
            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            active_processes.append(process)
            
            bot.send_message(message.chat.id, "✅ بدأ البث بنجاح على فيسبوك!")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ في تشغيل البث: {str(e)}")

@bot.message_handler(commands=['stop_all'])
def stop_all(message):
    global active_processes
    for p in active_processes:
        p.terminate()
    active_processes = []
    bot.reply_to(message, "🛑 تم إيقاف جميع عمليات البث.")

# تشغيل البوت
print("البوت يعمل الآن...")
bot.polling(none_stop=True)