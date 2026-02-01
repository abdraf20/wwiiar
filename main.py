import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import tweepy

# ================= إعدادات التوثيق (يجب تعبئتها) =================
# تويتر
API_KEY = '7y54FKPfLFIqxd84fjeQi5lwi'
API_SECRET = 'Cymdt4scVfMrpKEjOtlD3MGBy5gX1ixaq7iJ8tesxMfVA0Kq2T'
ACCESS_TOKEN = '1456970619342442499-vr8KB1movLCJPINeK39X8I3yXDWBZO'
ACCESS_TOKEN_SECRET = 'I3mEhIoaahQ1431dMMVaCZO80zvpSgIJMOXojPoyimDFV'

# تيليجرام
TELEGRAM_TOKEN = 'TuoBoHO3Nj14ifWE353UctGLmu5Q96oDSsl4DLpFTT494'
CHANNEL_USERNAME = '@WWIIIAR'  # مثال: @MyNewsChannel

# ================= تهيئة الاتصال بتويتر =================
# 1. نحتاج Client (v2) لنشر النصوص والتغريدات النهائية
client_v2 = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# 2. نحتاج API (v1.1) لرفع الوسائط (صور وفيديو)
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api_v1 = tweepy.API(auth)

# إعداد السجلات (Logging) لمراقبة الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def forward_to_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # --- كود تشخيص المشكلة ---
    if update.channel_post:
        chat_username = update.channel_post.chat.username
        print(f"⚠️ تنبيه: البوت استلم رسالة من القناة: @{chat_username}")
        print(f"   (القناة المطلوبة في الكود هي: {CHANNEL_USERNAME})")
    # --------------------------

    # التأكد أن الرسالة قادمة من القناة المحددة
    if not update.channel_post or update.channel_post.chat.username != CHANNEL_USERNAME.replace('@', ''):
        print("❌ تم تجاهل الرسالة لأن اسم القناة غير مطابق.")
        return

    # ... باقي الكود كما هو ...

    msg = update.channel_post
    media_ids = []
    temp_filename = ""
    
    # 1. استخراج النص (سواء كان رسالة عادية أو شرح للصورة/الفيديو)
    tweet_text = msg.caption if msg.caption else msg.text
    if tweet_text is None:
        tweet_text = "" # في حال كانت صورة بدون نص

    print(f"--> استلمت رسالة جديدة. النوع: {'ميديا' if msg.caption else 'نص'}")

    try:
        # ================= حالة 1: وجود صورة =================
        if msg.photo:
            print("   جاري تحميل الصورة...")
            # تيليجرام يرسل عدة جودات، نختار أعلاها (-1)
            file = await msg.photo[-1].get_file()
            temp_filename = f"temp_{msg.id}.jpg"
            await file.download_to_drive(temp_filename)
            
            print("   جاري رفع الصورة لتويتر...")
            media = api_v1.media_upload(filename=temp_filename)
            media_ids.append(media.media_id)

        # ================= حالة 2: وجود فيديو =================
        elif msg.video:
            print("   جاري تحميل الفيديو (قد يستغرق وقتاً)...")
            file = await msg.video.get_file()
            temp_filename = f"temp_{msg.id}.mp4"
            await file.download_to_drive(temp_filename)
            
            print("   جاري رفع الفيديو لتويتر...")
            # نستخدم chunked=True ضروري للفيديوهات
            media = api_v1.media_upload(
                filename=temp_filename, 
                chunked=True, 
                media_category='tweet_video'
            )
            media_ids.append(media.media_id)

        # ================= حالة 3: نص فقط (أو إتمام النشر للميديا) =================
        
        # معالجة طول النص (تويتر يقبل 280 حرف)
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        
        # النشر النهائي
        if tweet_text or media_ids:
            client_v2.create_tweet(text=tweet_text, media_ids=media_ids if media_ids else None)
            print("✅ تم النشر على تويتر بنجاح!")
        else:
            print("⚠️ الرسالة فارغة ولا تحتوي وسائط!")

    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

    finally:
        # تنظيف: حذف الملفات المؤقتة من السيرفر
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)
            print("   تم تنظيف الملفات المؤقتة.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # الفلتر يستقبل: نصوص، صور، فيديو
    app.add_handler(MessageHandler(
        filters.ChatType.CHANNEL & (filters.TEXT | filters.PHOTO | filters.VIDEO), 
        forward_to_twitter
    ))
    
    print("🤖 البوت يعمل الآن ويراقب القناة...")

    app.run_polling()


