import urllib.request
import json
import time

from config import TOKEN, MAINTENANCE_MODE, ADMIN_ID, TRANSLATION_ENABLED
from state import USER_STATE
from user_service import save_user
from database import execute

# executors
from executors import executor, coding_executor

# handlers
from menu_handler import handle_main_menu
from levels_handler import handle_levels
from files_handler import handle_files
from coding_handler import handle_coding
from broadcast_handler import handle_broadcast
from exam_handler import handle_exam

# 🔥 الترجمة
from translation_handler import handle_translation
from translation_queue import start_worker

from telegram_sender import send_message


print("Bot Started...")

# 🔥 تشغيل Worker واحد فقط
start_worker()

last_update_id = 0


# =========================
# معالجة كل رسالة
# =========================
def process_update(update):
    try:
        if "message" not in update:
            return

        message = update["message"]
        text = message.get("text") or ""

        user_data = message.get("from", {})

        chat_id = str(user_data.get("id"))
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        username = user_data.get("username", "")

        # =========================
        # تسجيل الرسائل
        # =========================
        if text:
            execute(
                """
                INSERT INTO messages (chat_id, first_name, username, message_text)
                VALUES (%s, %s, %s, %s)
                """,
                (chat_id, first_name, username, text)
            )

        # =========================
        # حفظ المستخدم
        # =========================
        save_user(chat_id, first_name, last_name, username)

        # =========================
        # تهيئة الحالة
        # =========================
        if chat_id not in USER_STATE:
            USER_STATE[chat_id] = "main"

        # =========================
        # وضع الصيانة
        # =========================
        if MAINTENANCE_MODE and chat_id != str(ADMIN_ID):
            send_message(chat_id, "البوت متوقف حالياً للتحديث، حاول لاحقاً.")
            return

        # =========================
        # 🔒 منع الترجمة قبل المينيو (الحل الأساسي)
        # =========================
        if not TRANSLATION_ENABLED and chat_id != str(ADMIN_ID):
            if text == "🌍 ترجمة المستندات":
                send_message(chat_id, "🚧 ميزة الترجمة قريبًا إن شاء الله")
                return

        # =========================
        # التوجيه (Handlers)
        # =========================

        if handle_broadcast(chat_id, text):
            return

        if handle_main_menu(chat_id, text):
            return

        # =========================
        # 🔒 حماية إضافية (لو دخل الحالة غصب)
        # =========================
        if not TRANSLATION_ENABLED and chat_id != str(ADMIN_ID):
            if USER_STATE.get(chat_id) == "translation_menu":
                USER_STATE[chat_id] = "main"
                send_message(chat_id, "🚧 ميزة الترجمة قريبًا إن شاء الله")
                return

        # 🔥 الترجمة (للأدمن أو إذا مفتوحة)
        if handle_translation(chat_id, text, message):
            return

        if handle_levels(chat_id, text):
            return

        if handle_files(chat_id, text):
            return

        if handle_exam(chat_id, text):
            return

        # =========================
        # coding (thread منفصل)
        # =========================
        coding_executor.submit(handle_coding, chat_id, text, message)

    except Exception as e:
        print("Thread Error:", e)
        try:
            send_message(chat_id, "حدث خطأ غير متوقع.")
        except:
            pass


# =========================
# Main Loop
# =========================
while True:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=10"

        response = urllib.request.urlopen(url, timeout=15)
        data = json.loads(response.read().decode("utf-8"))

        for update in data.get("result", []):
            last_update_id = update["update_id"]
            executor.submit(process_update, update)

    except Exception as e:
        error_text = str(e)

        if (
            "Connection reset by peer" in error_text
            or "timed out" in error_text
            or "Remote end closed connection" in error_text
        ):
            pass
        else:
            print("Main Error:", e)

        time.sleep(1)

    time.sleep(0.05)
