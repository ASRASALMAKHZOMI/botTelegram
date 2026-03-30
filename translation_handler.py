from state import USER_STATE
from telegram_sender import send_message
from translation_queue import add_task


# =========================
# القائمة الرئيسية
# =========================
def send_main_menu(chat_id):

    keyboard = [
        ["📚 الملازم", "📊 الجداول"],
        ["💻 تحدي البرمجة", "🧠 مساعد الدراسة الذكي"],
        ["🌍 ترجمة المستندات"],
        ["👤 من نحن"]
    ]

    send_message(chat_id, "اختر ما تحتاج:", keyboard)


# =========================
# Translation Handler
# =========================
def handle_translation(chat_id, text, message):

    state = USER_STATE.get(chat_id)

    # =========================
    # القائمة
    # =========================
    if state == "translation_menu":

        if text == "🔙 رجوع":
            USER_STATE[chat_id] = "main"
            USER_STATE.pop(chat_id + "_translation_mode", None)
            send_main_menu(chat_id)
            return True

        if text == "📂 اختيار من الملازم":
            USER_STATE[chat_id] = "choose_level"
            USER_STATE[chat_id + "_translation_mode"] = True

            keyboard = [
                ["📘 المستوى الأول"],
                ["📗 المستوى الثاني"],
                ["📙 المستوى الثالث"],
                ["📕 المستوى الرابع"],
                ["/start"]
            ]

            send_message(chat_id, "اختر المستوى:", keyboard)
            return True

        if text == "📤 رفع ملف":
            USER_STATE[chat_id] = "translation_upload"
            send_message(chat_id, "📤 أرسل ملف PDF الآن")
            return True

        return True


    # =========================
    # استقبال الملف
    # =========================
    if state == "translation_upload":

        if message and "document" in message:

            file_id = message["document"]["file_id"]

            add_task(file_id, chat_id)

            send_message(chat_id, "📥 تم استلام الملف وجاري المعالجة")

            # 🔥 تنظيف الحالة
            USER_STATE[chat_id] = "main"
            USER_STATE.pop(chat_id + "_translation_mode", None)

            # 🔥 إرجاع القائمة
            send_main_menu(chat_id)

            return True

        return True


    return False
