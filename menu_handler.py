from telegram_sender import send_message
from state import USER_STATE

# =========================
# Main Menu Handler
# =========================

def handle_main_menu(chat_id, text):

    # START
    if text == "/start":
        USER_STATE[chat_id] = "main"
        USER_STATE.pop(chat_id + "_exam_mode", None)

        keyboard = [
            ["📚 الملازم", "📊 الجداول"],
            ["💻 تحدي البرمجة", "🧠 مساعد الدراسة الذكي"],
            ["🌍 ترجمة المستندات"],
            ["👤 من نحن"]
        ]

        send_message(chat_id, "اهلًا بك، اختر ما تحتاجه:", keyboard)
        return True


    # لازم يكون في main
    if USER_STATE.get(chat_id) != "main":
        return False


    # الملازم
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


    # الجداول
    elif text == "📊 الجداول":
        send_message(chat_id, "سيتم إضافة الجداول قريباً.")
        return True


    # التحدي
    elif text == "💻 تحدي البرمجة":

        USER_STATE[chat_id] = "coding_level"

        intro_message = (
            "💻 نظام تقييم تحدي البرمجة\n\n"
            "يتم تقييمك بناءً على جودة الكود نفسه وليس صعوبة السؤال.\n\n"
            "مراحل التقييم 4 مستويات:\n\n"
            "1️⃣ مبتدى:\n"
            "حل مباشر وبسيط بدون تحسينات.\n\n"
            "2️⃣ جيد:\n"
            "حل صحيح ومنظم.\n\n"
            "3️⃣ متقدم:\n"
            "تفكير أعمق أو أسلوب ذكي في الحل.\n\n"
            "4️⃣ احترافي:\n"
            "حل فعال، منظم، يراعي الحالات الخاصة والحواف."
        )

        send_message(chat_id, intro_message)

        keyboard = [
            ["🟢 سهل"],
            ["🟡 متوسط"],
            ["🔴 صعب"],
            ["🔙 رجوع"]
        ]

        send_message(chat_id, "اختر مستوى التحدي:", keyboard)
        return True


    # مساعد الدراسة
    elif text == "🧠 مساعد الدراسة الذكي":
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


    # الترجمة (فقط state)
    elif text == "🌍 ترجمة المستندات":
        USER_STATE[chat_id] = "translation_menu"

        keyboard = [
            ["📂 اختيار من الملازم"],
            ["📤 رفع ملف"],
            ["🔙 رجوع"]
        ]

        send_message(chat_id, "اختر طريقة الترجمة:", keyboard)
        return True


    # من نحن
    elif text == "👤 من نحن":
        send_message(
            chat_id,
            "من نحن؟\n\n"
            "اسمي عبدالله المخزومي 👋\n"
            "مطور هذا البوت.\n\n"
            "📱 واتساب:\n"
            "https://wa.me/967773233938"
        )
        return True


    return False
