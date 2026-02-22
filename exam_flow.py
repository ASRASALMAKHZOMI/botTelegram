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
            
            keyboard = [
                ["✔️ صح وخطأ"],
                ["📝 اختيار من متعدد"],
                ["📄 مقالي"]
            ]
            
            return {
                "text": "اختر نوع الأسئلة:",
                "keyboard": keyboard
            }

        return "الرجاء إدخال رقم صحيح لصفحة النهاية."

    # ==============================
    # نوع الأسئلة
    # ==============================
    if USER_STATE.get(chat_id) == "exam_type":

        type_map = {
            "✔️ صح وخطأ": "صح وخطأ",
            "📝 اختيار من متعدد": "اختيار من متعدد",
            "📄 مقالي": "مقالي"
        }

        if text in type_map:
            USER_STATE[chat_id + "_type"] = type_map[text]
            USER_STATE[chat_id] = "exam_count"
            keyboard = [
                ["5", "10"],
                ["15", "20"]
            ]
            
            return {
                "text": "اختر عدد الأسئلة:",
                "keyboard": keyboard
            }
            
        return "اختر من الأزرار المتاحة."

    # ==============================
    # عدد الأسئلة
    # ==============================
    if USER_STATE.get(chat_id) == "exam_count":

        if text in ["5", "10", "15", "20" , "25" , "30"]:

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

        return "اختر عدد الأسئلة من الأزرار."

    return None
