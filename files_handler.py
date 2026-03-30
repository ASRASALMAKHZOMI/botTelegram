import os
import fitz
from state import USER_STATE
from telegram_sender import send_message, send_file, remove_keyboard
from file_service import get_sorted_files
from translation_queue import add_task  # 🔥 إضافة


# =========================
# Files Handler
# =========================

def handle_files(chat_id, text):

    current_state = USER_STATE.get(chat_id)

    # =========================
    # عرض الملفات بعد اختيار مادة أو فرع
    # =========================

    if current_state in ["subjects", "exam_subject", "sub_subjects"]:

        subject_path = USER_STATE.get(chat_id + "_subject_path")

        if not subject_path:
            return False

        files = get_sorted_files(subject_path)

        if not files:
            return False

        # 🔥 تعديل هنا
        if USER_STATE.get(chat_id + "_exam_mode"):
            USER_STATE[chat_id] = "exam_file_select"

        elif USER_STATE.get(chat_id + "_translation_mode"):
            USER_STATE[chat_id] = "translation_file_select"

        else:
            USER_STATE[chat_id] = "files"

        USER_STATE[chat_id + "_files"] = files
        USER_STATE[chat_id + "_path"] = subject_path

        keyboard = [[os.path.splitext(f)[0]] for f in files]
        keyboard.append(["🔙 رجوع"])

        send_message(chat_id, "اختر الملف:", keyboard)
        return True


    # =========================
    # FILES (إرسال PDF عادي)
    # =========================

    if current_state == "files":

        if text == "🔙 رجوع":

            if chat_id + "_sub_subjects" in USER_STATE:

                USER_STATE[chat_id] = "sub_subjects"

                sub_subjects = USER_STATE.get(chat_id + "_sub_subjects", [])
                keyboard = [[s] for s in sub_subjects]
                keyboard.append(["🔙 رجوع"])

                send_message(chat_id, "اختر:", keyboard)

            else:
                USER_STATE[chat_id] = "subjects"

                subjects = USER_STATE.get(chat_id + "_subjects", [])
                keyboard = [[subject] for subject in subjects]
                keyboard.append(["🔙 رجوع"])

                send_message(chat_id, "المواد المتوفرة:", keyboard)

            return True

        files = USER_STATE.get(chat_id + "_files", [])
        subject_path = USER_STATE.get(chat_id + "_path")

        for file in files:
            if text == os.path.splitext(file)[0]:
                send_file(chat_id, os.path.join(subject_path, file))
                return True

        return False


    # =========================
    # 🔥 TRANSLATION FILE SELECT (الجديد)
    # =========================

    if current_state == "translation_file_select":

        if text == "🔙 رجوع":

            USER_STATE[chat_id] = "subjects"

            subjects = USER_STATE.get(chat_id + "_subjects", [])
            keyboard = [[subject] for subject in subjects]
            keyboard.append(["🔙 رجوع"])

            send_message(chat_id, "المواد المتوفرة:", keyboard)
            return True

        files = USER_STATE.get(chat_id + "_files", [])
        subject_path = USER_STATE.get(chat_id + "_path")

        for file in files:
            if text == os.path.splitext(file)[0]:

                pdf_path = os.path.join(subject_path, file)

                # 🔥 نرسله للترجمة مباشرة
                add_task(pdf_path, chat_id)

                send_message(chat_id, "📥 تم إرسال الملف للترجمة...")

                USER_STATE[chat_id] = "main"
                USER_STATE.pop(chat_id + "_translation_mode", None)

                return True

        return False


    # =========================
    # EXAM FILE SELECT
    # =========================

    if current_state == "exam_file_select":

        if text == "🔙 رجوع":

            USER_STATE[chat_id] = "subjects"

            subjects = USER_STATE.get(chat_id + "_subjects", [])
            keyboard = [[subject] for subject in subjects]
            keyboard.append(["🔙 رجوع"])

            send_message(chat_id, "المواد المتوفرة:", keyboard)
            return True

        files = USER_STATE.get(chat_id + "_files", [])
        subject_path = USER_STATE.get(chat_id + "_path")

        for file in files:
            if text == os.path.splitext(file)[0]:

                pdf_path = os.path.join(subject_path, file)

                # 🔥 قراءة عدد الصفحات
                try:
                    doc = fitz.open(pdf_path)
                    total_pages = len(doc)
                    doc.close()
                except Exception:
                    send_message(chat_id, "❌ حدث خطأ أثناء قراءة الملف.")
                    return True

                # تخزين البيانات
                USER_STATE[chat_id + "_pdf"] = pdf_path
                USER_STATE[chat_id + "_total_pages"] = total_pages
                USER_STATE[chat_id] = "exam_start_page"

                remove_keyboard(
                    chat_id,
                    f"📄 هذا الملف يحتوي على {total_pages} صفحة.\n\nأدخل صفحة البداية:"
                )

                return True

        return False


    return False
