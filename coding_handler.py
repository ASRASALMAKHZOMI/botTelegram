import time
import threading
import urllib.request
import json

from state import USER_STATE
from telegram_sender import send_message, remove_keyboard
from ai_service import generate_challenge, evaluate_code, call_ai
from config import TOKEN


# =========================
# التحقق من أن النص كود (نعم / لا)
# =========================

def is_code(text):

    validation_messages = [
        {
            "role": "system",
            "content": "حدد هل النص التالي كود برمجي فعلي. أجب فقط بكلمة واحدة بدون أي شرح: نعم أو لا."
        },
        {
            "role": "user",
            "content": text
        }
    ]

    result = call_ai(
        validation_messages,
        temperature=0,
        max_tokens=3
    ).strip().lower()

    return result == "نعم"


# =========================
# تحميل ملف من Telegram
# =========================

def load_file_content(file_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode("utf-8"))

        file_path = data["result"]["file_path"]

        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        file_response = urllib.request.urlopen(download_url)
        content = file_response.read().decode("utf-8")

        return content

    except Exception as e:
        print("FILE LOAD ERROR:", e)
        return ""


# =========================
# Coding Challenge Handler
# =========================

def handle_coding(chat_id, text, message=None):

    current_state = USER_STATE.get(chat_id)

    # =========================
    # اختيار المستوى
    # =========================

    if current_state == "coding_level":

        if text == "🔙 رجوع":
            USER_STATE[chat_id] = "main"

            keyboard = [
                ["📚 الملازم", "📊 الجداول"],
                ["💻 تحدي البرمجة", "🧠 مساعد الدراسة الذكي"],
                ["👤 من نحن"]
            ]

            send_message(chat_id, "اهلًا بك، اختر ما تحتاجه:", keyboard)
            return True

        level_map = {
            "🟢 سهل": "سهل",
            "🟡 متوسط": "متوسط",
            "🔴 صعب": "صعب"
        }

        if text not in level_map:
            send_message(chat_id, "اختيار غير صحيح.")
            return True

        level = level_map[text]

        send_message(chat_id, "جاري إنشاء التحدي...")
        challenge = generate_challenge(level)

        USER_STATE[chat_id] = "coding_challenge_menu"
        USER_STATE[chat_id + "_challenge"] = challenge
        USER_STATE[chat_id + "_level"] = level

        keyboard = [
            ["🔄 إعادة السؤال"],
            ["💡 حل السؤال"],
            ["🔙 رجوع"]
        ]

        send_message(chat_id, challenge, keyboard)
        return True


    # =========================
    # قائمة التحدي
    # =========================

    if current_state == "coding_challenge_menu":

        if text == "🔙 رجوع":

            USER_STATE[chat_id] = "coding_level"

            keyboard = [
                ["🟢 سهل"],
                ["🟡 متوسط"],
                ["🔴 صعب"],
                ["🔙 رجوع"]
            ]

            send_message(chat_id, "اختر مستوى التحدي:", keyboard)
            return True

        if text == "🔄 إعادة السؤال":

            level = USER_STATE.get(chat_id + "_level")

            send_message(chat_id, "جاري إنشاء تحدي جديد...")
            challenge = generate_challenge(level)

            USER_STATE[chat_id + "_challenge"] = challenge

            keyboard = [
                ["🔄 إعادة السؤال"],
                ["💡 حل السؤال"],
                ["🔙 رجوع"]
            ]

            send_message(chat_id, challenge, keyboard)
            return True

        if text == "💡 حل السؤال":

            USER_STATE[chat_id] = "coding_wait_code"
            USER_STATE[chat_id + "_code_buffer"] = ""
            USER_STATE[chat_id + "_last_code_time"] = 0

            remove_keyboard(
                chat_id,
                "💻 أرسل الكود الآن.\n\n"
                "⚠ تنبيه مهم:\n"
                "إذا كان الكود يحتوي على معاملات منطقية مثل && أو ||\n"
                "يفضل إرساله كملف .txt أو بأي امتداد ملف مناسب للغة المستخدمة\n"
                "لتجنب مشاكل التنسيق.\n\n"
                "يمكنك إرسال الكود كنص أو كملف."
            )
            return True

        send_message(chat_id, "اختر من الأزرار المتاحة.")
        return True


    # =========================
    # استقبال الكود
    # =========================

    if current_state == "coding_wait_code":

        challenge = USER_STATE.get(chat_id + "_challenge")
        if not challenge:
            USER_STATE[chat_id] = "coding_level"
            return True

        # =========================
        # رفع ملف
        # =========================

        if message and "document" in message:

            send_message(chat_id, "📎 تم استلام الملف.\n⏳ جاري التحقق من المحتوى...")

            file_id = message["document"]["file_id"]
            code_text = load_file_content(file_id)

            if not code_text.strip():
                send_message(chat_id, "❌ فشل قراءة الملف.")
                return True

            if not is_code(code_text):
                send_message(
                    chat_id,
                    "❌ الملف لا يحتوي على كود برمجي واضح.\n\n"
                    "💻 أرسل الكود الصحيح لإكمال التقييم."
                )
                return True

            send_message(chat_id, "⏳ جاري تقييم الحل...")
            evaluation = evaluate_code(challenge, code_text)

            send_message(chat_id, evaluation)
            _reset_coding_state(chat_id)
            return True


        # =========================
        # استقبال نص مباشر
        # =========================

        code_text = text.strip()
        if len(code_text) < 3:
            return True

        if not is_code(code_text):
            send_message(
                chat_id,
                "❌ النص المرسل لا يبدو كوداً برمجياً.\n\n"
                "💻 أرسل الكود الصحيح لإكمال التقييم."
            )
            return True

        is_first_chunk = not USER_STATE.get(chat_id + "_code_buffer")

        USER_STATE[chat_id + "_code_buffer"] += code_text + "\n"
        USER_STATE[chat_id + "_last_code_time"] = time.time()

        if is_first_chunk:
            send_message(chat_id, "📥 تم استلام الكود.")
        else:
            send_message(chat_id, "📥 تم استلام جزء إضافي من الكود.")

        def check_complete():
            time.sleep(1.5)

            last_time = USER_STATE.get(chat_id + "_last_code_time", 0)

            if time.time() - last_time >= 1.5:

                final_code = USER_STATE.get(chat_id + "_code_buffer", "")

                send_message(chat_id, "⏳ جاري تقييم الحل...")
                evaluation = evaluate_code(challenge, final_code)

                send_message(chat_id, evaluation)
                _reset_coding_state(chat_id)

        threading.Thread(target=check_complete).start()
        return True

    return False


# =========================
# إعادة الحالة بعد التقييم فقط
# =========================

def _reset_coding_state(chat_id):

    USER_STATE[chat_id] = "coding_level"

    USER_STATE.pop(chat_id + "_challenge", None)
    USER_STATE.pop(chat_id + "_level", None)
    USER_STATE.pop(chat_id + "_code_buffer", None)
    USER_STATE.pop(chat_id + "_last_code_time", None)

    keyboard = [
        ["🟢 سهل"],
        ["🟡 متوسط"],
        ["🔴 صعب"],
        ["🔙 رجوع"]
    ]

    send_message(chat_id, "اختر مستوى جديد:", keyboard)
