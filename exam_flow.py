import os

def handle_exam_flow(chat_id, text, USER_STATE):

    # ==============================
    # بدء إدخال نطاق الصفحات
    # ==============================
    if USER_STATE.get(chat_id) == "exam_start_page":

        if text.isdigit():
            USER_STATE[chat_id + "_start"] = int(text)
            USER_STATE[chat_id] = "exam_end_page"
            return "أدخل صفحة النهاية:"

        return "الرجاء إدخال رقم صحيح لصفحة البداية."

    # ==============================
    # صفحة النهاية
    # ==============================
    if USER_STATE.get(chat_id) == "exam_end_page":

        if text.isdigit():
            USER_STATE[chat_id + "_end"] = int(text)
            USER_STATE[chat_id] = "exam_type"

            return (
                "اختر نوع الأسئلة:\n"
                "1- صح وخطأ\n"
                "2- اختيار من متعدد\n"
                "3- مقالي"
            )

        return "الرجاء إدخال رقم صحيح لصفحة النهاية."

    # ==============================
    # نوع الأسئلة
    # ==============================
    if USER_STATE.get(chat_id) == "exam_type":

        type_map = {
            "1": "صح وخطأ",
            "2": "اختيار من متعدد",
            "3": "مقالي"
        }

        if text in type_map:
            USER_STATE[chat_id + "_type"] = type_map[text]
            USER_STATE[chat_id] = "exam_count"
            return "كم عدد الأسئلة؟"

        return "اختر رقم صحيح: 1 أو 2 أو 3."

    # ==============================
    # عدد الأسئلة
    # ==============================
    if USER_STATE.get(chat_id) == "exam_count":

        if text.isdigit():

            pdf = USER_STATE.get(chat_id + "_pdf")
            start = USER_STATE.get(chat_id + "_start")
            end = USER_STATE.get(chat_id + "_end")
            qtype = USER_STATE.get(chat_id + "_type")
            count = int(text)

            # رجوع للقائمة الرئيسية
            USER_STATE[chat_id] = "main"

            # نخزن بيانات مؤقتة ليتم تنفيذها في bot.py
            USER_STATE[chat_id + "_exam_ready"] = (
                pdf, start, end, qtype, count
            )

            return "جاري إنشاء الأسئلة، انتظر قليلاً..."

        return "أدخل رقم صحيح لعدد الأسئلة."

    return None
