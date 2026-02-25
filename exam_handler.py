from state import USER_STATE
from telegram_sender import send_message, remove_keyboard
from exam_module import generate_exam


# =========================
# Exam Handler
# =========================

def handle_exam(chat_id, text):

    current_state = USER_STATE.get(chat_id)

    # =========================
    # مرحلة إدخال صفحة البداية
    # =========================

    if current_state == "exam_start_page":

        if not text.isdigit():
            send_message(chat_id, "❌ أدخل رقم صفحة صحيح.")
            return True

        USER_STATE[chat_id + "_start"] = int(text)
        USER_STATE[chat_id] = "exam_end_page"

        send_message(chat_id, "أدخل صفحة النهاية:")
        return True


    # =========================
    # مرحلة إدخال صفحة النهاية
    # =========================

    if current_state == "exam_end_page":

        if not text.isdigit():
            send_message(chat_id, "❌ أدخل رقم صفحة صحيح.")
            return True

        USER_STATE[chat_id + "_end"] = int(text)
        USER_STATE[chat_id] = "exam_type"

        keyboard = [
            ["اختياري"],
            ["صح أو خطأ"],
            ["مقالي"]
        ]

        send_message(chat_id, "اختر نوع الأسئلة:", keyboard)
        return True


    # =========================
    # نوع الأسئلة
    # =========================

    if current_state == "exam_type":

        if text not in ["اختياري", "صح أو خطأ", "مقالي"]:
            send_message(chat_id, "❌ اختر من الخيارات المتاحة.")
            return True

        USER_STATE[chat_id + "_type"] = text
        USER_STATE[chat_id] = "exam_count"

        # 🔥 أزرار عدد الأسئلة
        keyboard = [
            ["5", "10"],
            ["15", "20"]
        ]

        send_message(chat_id, "كم عدد الأسئلة؟", keyboard)
        return True


    # =========================
    # عدد الأسئلة
    # =========================

    if current_state == "exam_count":

        if text not in ["5", "10", "15", "20"]:
            send_message(chat_id, "❌ اختر عدد من الأزرار المتاحة.")
            return True

        count = int(text)

        USER_STATE[chat_id + "_count"] = count

        pdf = USER_STATE.get(chat_id + "_pdf")
        start = USER_STATE.get(chat_id + "_start")
        end = USER_STATE.get(chat_id + "_end")
        qtype = USER_STATE.get(chat_id + "_type")

        # إزالة الكيبورد قبل الإنشاء
        remove_keyboard(chat_id, "⏳ جاري إنشاء الامتحان...")

        result = generate_exam(pdf, start, end, qtype, count)

        send_message(chat_id, result)

        # تنظيف الحالة
        USER_STATE.pop(chat_id + "_exam_mode", None)
        USER_STATE.pop(chat_id + "_start", None)
        USER_STATE.pop(chat_id + "_end", None)
        USER_STATE.pop(chat_id + "_type", None)
        USER_STATE.pop(chat_id + "_count", None)
        USER_STATE.pop(chat_id + "_pdf", None)

        USER_STATE[chat_id] = "main"

        keyboard = [
            ["📚 الملازم", "📊 الجداول"],
            ["💻 تحدي البرمجة", "📝 توليد أسئلة امتحانية"],
            ["👤 من نحن"]
        ]

        send_message(chat_id, "تم إرجاعك للقائمة الرئيسية.", keyboard)
        return True


    return False
