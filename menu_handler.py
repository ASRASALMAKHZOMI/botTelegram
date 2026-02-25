from telegram_sender import send_message
from state import USER_STATE

# =========================
# Main Menu Handler
# =========================

def handle_main_menu(chat_id, text):

    # أمر البدء
    if text == "/start":
        USER_STATE[chat_id] = "main"

        # تنظيف أي وضع امتحان سابق
        USER_STATE.pop(chat_id + "_exam_mode", None)

        keyboard = [
            ["📚 الملازم", "📊 الجداول"],
            ["💻 تحدي البرمجة", "📝 توليد أسئلة امتحانية"],
            ["👤 من نحن"]
        ]

        send_message(chat_id, "اهلًا بك، اختر ما تحتاجه:", keyboard)
        return True


    # =========================
    # MAIN STATE
    # =========================

    if USER_STATE.get(chat_id) != "main":
        return False


    if text == "📚 الملازم":
        USER_STATE[chat_id] = "choose_level"

        keyboard = [
            ["📘 المستوى الأول"],
            ["📗 المستوى الثاني"],
            ["📙 المستوى الثالث"],
            ["📕 المستوى الرابع"],
            ["/start"]
        ]

        send_message(chat_id, "اختر المستوى:", keyboard)
        return True


    elif text == "📊 الجداول":
        send_message(chat_id, "سيتم إضافة الجداول قريباً.")
        return True


    elif text == "💻 تحدي البرمجة":
        USER_STATE[chat_id] = "coding_level"

        keyboard = [
            ["🟢 سهل"],
            ["🟡 متوسط"],
            ["🔴 صعب"],
            ["🔙 رجوع"]
        ]

        send_message(chat_id, "اختر مستوى التحدي:", keyboard)
        return True


    elif text == "📝 توليد أسئلة امتحانية":
        USER_STATE[chat_id] = "choose_level"
        USER_STATE[chat_id + "_exam_mode"] = True

        keyboard = [
            ["📘 المستوى الأول"],
            ["📗 المستوى الثاني"],
            ["📙 المستوى الثالث"],
            ["📕 المستوى الرابع"],
            ["/start"]
        ]

        send_message(chat_id, "اختر المستوى:", keyboard)
        return True


    elif text == "👤 من نحن":
        send_message(
            chat_id,
            "من نحن؟\n\n"
            "اسمي عبدالله المخزومي 👋\n"
            "مطور هذا البوت لخدمة الطلاب وتسهيل الوصول للملازم وتطوير مهاراتهم البرمجية وغير ذلك."
        )
        return True


    return False