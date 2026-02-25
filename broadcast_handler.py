from config import ADMIN_ID
from user_service import get_all_users
from telegram_sender import send_message
import time


# =========================
# Broadcast Handler
# =========================

def handle_broadcast(chat_id, text):

    # ليس أمر بث
    if not text.startswith("/broadcast"):
        return False

    # ليس الأدمن
    if str(chat_id) != str(ADMIN_ID):
        return True  # نمنع التنفيذ بدون ما نكمل

    message = text.replace("/broadcast", "").strip()

    if not message:
        send_message(chat_id, "اكتب الرسالة بعد الأمر.")
        return True

    users = get_all_users()
    sent = 0

    for user in users:
        try:
            send_message(user, f"📢 إشعار من الإدارة:\n\n{message}")
            sent += 1
            time.sleep(0.05)
        except:
            pass

    send_message(chat_id, f"تم إرسال الرسالة إلى {sent} مستخدم.")
    return True