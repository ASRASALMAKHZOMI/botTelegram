import urllib.request
import json
import time
import threading
import os
from flask import Flask

from config import TOKEN, MAINTENANCE_MODE, ADMIN_ID
from state import USER_STATE
from user_service import save_user
from database import cur, conn

from menu_handler import handle_main_menu
from levels_handler import handle_levels
from files_handler import handle_files
from coding_handler import handle_coding
from broadcast_handler import handle_broadcast
from exam_handler import handle_exam

from telegram_sender import send_message


# =========================
# Flask (حل مشكلة Render)
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# تشغيل Flask في الخلفية
threading.Thread(target=run_web).start()


print("Bot Started...")

last_update_id = 0


# =========================
# Main Loop
# =========================

while True:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode("utf-8"))

        for update in data.get("result", []):

            last_update_id = update["update_id"]

            if "message" not in update:
                continue

            message = update["message"]
            text = message.get("text", "")
            user_data = message.get("from", {})

            chat_id = str(user_data.get("id"))
            first_name = user_data.get("first_name", "")
            last_name = user_data.get("last_name", "")
            username = user_data.get("username", "")

            # =========================
            # تسجيل الرسائل
            # =========================
            try:
                if text:
                    cur.execute(
                        """
                        INSERT INTO messages (chat_id, first_name, username, message_text)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (chat_id, first_name, username, text)
                    )
                    conn.commit()
            except:
                pass

            # حفظ المستخدم
            save_user(chat_id, first_name, last_name, username)

            # تهيئة الحالة
            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"

            # =========================
            # وضع الصيانة
            # =========================
            if MAINTENANCE_MODE and chat_id != str(ADMIN_ID):
                send_message(chat_id, "البوت متوقف حالياً.")
                continue

            # =========================
            # Handlers
            # =========================

            if handle_broadcast(chat_id, text):
                continue

            if handle_main_menu(chat_id, text):
                continue

            if handle_levels(chat_id, text):
                continue

            if handle_files(chat_id, text):
                continue

            if handle_exam(chat_id, text):
                continue

            if handle_coding(chat_id, text, message):
                continue


    except Exception as e:
        print("Error:", e)
        try:
            send_message(chat_id, "حدث خطأ غير متوقع. حاول مرة أخرى.")
        except:
            pass

    time.sleep(0.3)
