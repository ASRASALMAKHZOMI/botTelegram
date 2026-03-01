import time
import threading
from state import USER_STATE
from telegram_sender import send_message, remove_keyboard
from ai_service import generate_challenge, evaluate_code, call_ai

# =========================
# Coding Challenge Handler
# =========================

def handle_coding(chat_id, text, message=None):

    current_state = USER_STATE.get(chat_id)

    # =========================
    # اختيار مستوى التحدي
    # =========================

    if current_state == "coding_level":

        if text == "🔙 رجوع":

            USER_STATE[chat_id] = "main"

            keyboard = [
                ["📚 الملازم", "📊 الجداول"],
                ["💻 تحدي البرمجة", "📝 توليد أسئلة امتحانية"],
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
    # بعد عرض التحدي
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

            remove_keyboard(chat_id,
                "💻 أرسل الكود الآن.\n\n"
                "إذا كان الكود طويلًا يمكنك إرساله كملف.\n"
                "إذا أرسلته كنص طويل سيتم تجميعه تلقائيًا."
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
        # دعم رفع ملف
        # =========================

        if message and "document" in message:

            send_message(chat_id, "📎 تم استلام الملف.\n⏳ جاري تقييم الحل...")

            # هنا تحتاج تضيف دالة تحميل الملف حسب نظامك
            code_text = load_file_content(message["document"]["file_id"])

            evaluation = evaluate_code(challenge, code_text)

            _reset_coding_state(chat_id)
            send_message(chat_id, evaluation)
            return True

        # =========================
        # تجميع النصوص الطويلة
        # =========================

        code_text = text.strip()
        if len(code_text) < 3:
            return True

        is_first_chunk = not USER_STATE.get(chat_id + "_code_buffer")

        USER_STATE[chat_id + "_code_buffer"] += code_text + "\n"
        USER_STATE[chat_id + "_last_code_time"] = time.time()

        if is_first_chunk:
            send_message(chat_id, "📥 تم استلام الكود.")
        else:
            send_message(chat_id, "📥 تم استلام الكود مكمل للسابق.")

        def check_complete():

            time.sleep(1.5)

            last_time = USER_STATE.get(chat_id + "_last_code_time", 0)

            if time.time() - last_time >= 1.5:

                final_code = USER_STATE.get(chat_id + "_code_buffer", "")
                send_message(chat_id, "⏳ جاري تقييم الحل...")

                evaluation = evaluate_code(challenge, final_code)

                _reset_coding_state(chat_id)
                send_message(chat_id, evaluation)

        threading.Thread(target=check_complete).start()
        return True

    return False


# =========================
# إعادة ضبط الحالة
# =========================

def _reset_coding_state(chat_id):

    USER_STATE[chat_id] = "coding_level"
    USER_STATE.pop(chat_id + "_challenge", None)
    USER_STATE.pop(chat_id + "_level", None)
    USER_STATE.pop(chat_id + "_code_buffer", None)
    USER_STATE.pop(chat_id + "_last_code_time", None)
