import threading
from state import USER_STATE
from telegram_sender import send_message, remove_keyboard
from exam_module import generate_exam, generate_explanation, generate_terms


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

        start_page = int(text)
        total_pages = USER_STATE.get(chat_id + "_total_pages")

        if not total_pages:
            send_message(chat_id, "حدث خطأ في بيانات الملف. أعد المحاولة.")
            USER_STATE[chat_id] = "main"
            return True

        if start_page < 1 or start_page > total_pages:
            send_message(chat_id, f"❌ يجب أن تكون الصفحة بين 1 و {total_pages}.")
            return True

        USER_STATE[chat_id + "_start"] = start_page
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

        end_page = int(text)
        start_page = USER_STATE.get(chat_id + "_start")
        total_pages = USER_STATE.get(chat_id + "_total_pages")

        if end_page < start_page:
            send_message(chat_id, "❌ صفحة النهاية يجب أن تكون أكبر من أو تساوي صفحة البداية.")
            return True

        if end_page > total_pages:
            send_message(chat_id, f"❌ لا يمكن تجاوز الصفحة {total_pages}.")
            return True

        USER_STATE[chat_id + "_end"] = end_page
        USER_STATE[chat_id] = "exam_type"

        total_selected = end_page - start_page + 1

        keyboard = [
            ["اختياري"],
            ["صح أو خطأ"],
            ["📘 شرح الملزمة"],
            ["📚 المصطلحات المتعلقة بالمادة"]
        ]

        send_message(
            chat_id,
            f"📄 تم اختيار {total_selected} صفحة.\n\nاختر نوع العملية:",
            keyboard
        )

        return True


    # =========================
    # اختيار نوع العملية
    # =========================

    if current_state == "exam_type":

        if text not in [
            "اختياري",
            "صح أو خطأ",
            "📘 شرح الملزمة",
            "📚 المصطلحات المتعلقة بالمادة"
        ]:
            send_message(chat_id, "❌ اختر من الخيارات المتاحة.")
            return True

        pdf = USER_STATE.get(chat_id + "_pdf")
        start = USER_STATE.get(chat_id + "_start")
        end = USER_STATE.get(chat_id + "_end")

        # =====================================
        # شرح الملزمة (Threaded)
        # =====================================

        if text == "📘 شرح الملزمة":

            remove_keyboard(chat_id, "⏳ جاري إنشاء الشرح...")

            def background_explanation():
                try:
                    result = generate_explanation(pdf, start, end)
                    send_message(chat_id, result)
                finally:
                    _reset_exam_state(chat_id)

            threading.Thread(target=background_explanation).start()
            return True


        # =====================================
        # المصطلحات (Threaded)
        # =====================================

        if text == "📚 المصطلحات المتعلقة بالمادة":

            remove_keyboard(chat_id, "⏳ جاري استخراج المصطلحات...")

            def background_terms():
                try:
                    result = generate_terms(pdf, start, end)
                    send_message(chat_id, result)
                finally:
                    _reset_exam_state(chat_id)

            threading.Thread(target=background_terms).start()
            return True


        # =====================================
        # توليد أسئلة
        # =====================================

        USER_STATE[chat_id + "_type"] = text
        USER_STATE[chat_id] = "exam_count"

        keyboard = [
            ["5", "10"],
            ["15", "20"]
        ]

        send_message(chat_id, "كم عدد الأسئلة؟", keyboard)
        return True


    # =========================
    # عدد الأسئلة (Threaded)
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

        remove_keyboard(chat_id, "⏳ جاري إنشاء الامتحان...")

        def background_exam():
            try:
                result = generate_exam(pdf, start, end, qtype, count)
                send_message(chat_id, result)
            finally:
                _reset_exam_state(chat_id)

        threading.Thread(target=background_exam).start()
        return True


    return False


# =========================
# Reset Exam State Helper
# =========================

def _reset_exam_state(chat_id):

    USER_STATE.pop(chat_id + "_exam_mode", None)
    USER_STATE.pop(chat_id + "_start", None)
    USER_STATE.pop(chat_id + "_end", None)
    USER_STATE.pop(chat_id + "_type", None)
    USER_STATE.pop(chat_id + "_count", None)
    USER_STATE.pop(chat_id + "_pdf", None)
    USER_STATE.pop(chat_id + "_total_pages", None)

    USER_STATE[chat_id] = "main"

    keyboard = [
    ["📚 الملازم", "📊 الجداول"],
    ["💻 تحدي البرمجة", "🧠 مساعد الدراسة الذكي"],
    ["👤 من نحن"]
    ]

    send_message(chat_id, "تم إرجاعك للقائمة الرئيسية.", keyboard)

