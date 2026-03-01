import telebot
from telebot import types
import subprocess
import threading
import time
import os

# إعدادات البوت
TOKEN = '8532448939:AAHt3VRMnROqmemsvFbWsTjpapRotelbOng'
bot = telebot.TeleBot(TOKEN)

# تخزين بيانات المستخدمين
user_sessions = {}

# دالة بناء الأوامر والقائمة
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 بدء بث مباشر", "🛑 إيقاف البث")
    markup.add("📝 نص الشريط المتحرك", "⚙️ حالة البث")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    user_sessions[cid] = {
        'rtmps': None, 
        'm3u8': None, 
        'ticker': "قناة البث المباشر - تابعونا", 
        'active': False
    }
    bot.send_message(cid, "🌟 مرحبا بك في نظام البث الاحترافي v3\nتم تفعيل نظام التشغيل المستمر (24/7).", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📝 نص الشريط المتحرك")
def set_ticker(message):
    msg = bot.send_message(message.chat.id, "أرسل النص اللي بغيتي يدوز لتحت (مثلاً: مرحبا بكم في قناتنا...):")
    bot.register_next_step_handler(msg, save_ticker)

def save_ticker(message):
    user_sessions[message.chat.id]['ticker'] = message.text
    bot.send_message(message.chat.id, f"✅ تم تحديث شريط الأخبار: {message.text}")

@bot.message_handler(func=lambda m: m.text == "🚀 بدء بث مباشر")
def get_rtmps(message):
    msg = bot.send_message(message.chat.id, "🔗 أرسل رابط RTMPS الكامل:")
    bot.register_next_step_handler(msg, get_m3u8)

def get_m3u8(message):
    user_sessions[message.chat.id]['rtmps'] = message.text
    msg = bot.send_message(message.chat.id, "📺 أرسل رابط M3U8 (المصدر):")
    bot.register_next_step_handler(msg, start_engine)

def start_engine(message):
    cid = message.chat.id
    user_sessions[cid]['m3u8'] = message.text
    user_sessions[cid]['active'] = True
    
    bot.send_message(cid, "🚀 تم تفعيل البث بنجاح! النظام سيقوم بإعادة التشغيل تلقائياً في حال الانقطاع.")
    
    # تشغيل البث في Thread منفصل مع خاصية الـ Auto-Restart
    threading.Thread(target=stream_monitor, args=(cid,), daemon=True).start()

def stream_monitor(cid):
    """دالة مراقبة البث وإعادة تشغيله تلقائياً"""
    while user_sessions.get(cid) and user_sessions[cid]['active']:
        config = user_sessions[cid]
        m3u8 = config['m3u8']
        rtmps = config['rtmps']
        ticker = config['ticker']

        # فلتر العلامة المائية المتحركة (Scrolling Text)
        # x=w-mod(t*100\,w+tw) تجعل النص يتحرك من اليمين لليسر
        filter_complex = (
            f"drawtext=text='{ticker}':x=w-mod(t*100\,w+tw):y=h-50:"
            f"fontsize=30:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5"
        )

        command = [
            'ffmpeg',
            '-re',
            '-i', m3u8,
            '-vf', filter_complex,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-b:v', '3000k', # جودة الفيديو
            '-maxrate', '3000k',
            '-bufsize', '6000k',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-f', 'flv',
            rtmps
        ]

        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            user_sessions[cid]['process'] = process
            process.wait() # انتظر حتى يسقط البث
        except Exception as e:
            print(f"Error: {e}")
        
        # إذا كان البث لا يزال مطلوباً، انتظر 5 ثواني وأعد التشغيل
        if user_sessions[cid]['active']:
            time.sleep(5)
            # يمكن إرسال تنبيه للمستخدم هنا (اختياري)

@bot.message_handler(func=lambda m: m.text == "🛑 إيقاف البث")
def stop_all(message):
    cid = message.chat.id
    if cid in user_sessions:
        user_sessions[cid]['active'] = False
        if 'process' in user_sessions[cid]:
            user_sessions[cid]['process'].terminate()
        bot.send_message(cid, "🛑 تم إيقاف البث ونظام المراقبة.")

@bot.message_handler(func=lambda m: m.text == "⚙️ حالة البث")
def status(message):
    cid = message.chat.id
    status_msg = "🟢 البث شغال حالياً" if user_sessions.get(cid, {}).get('active') else "🔴 البث متوقف"
    bot.send_message(cid, f"وضع النظام: {status_msg}")

# تشغيل البوت
bot.remove_webhook()
print("--- البوت الهربان شغال دابا ---")
bot.infinity_polling()
