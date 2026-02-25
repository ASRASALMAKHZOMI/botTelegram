import os
from state import USER_STATE
from telegram_sender import send_message, send_file
from file_service import get_sorted_files


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

        # تحديد وضع الامتحان أو العادي
        if USER_STATE.get(chat_id + "_exam_mode"):
            USER_STATE[chat_id] = "exam_file_select"
        else:
            USER_STATE[chat_id] = "files"

        USER_STATE[chat_id + "_files"] = files
        USER_STATE[chat_id + "_path"] = subject_path

        keyboard = [[os.path.splitext(f)[0]] for f in files]
        keyboard.append(["🔙 رجوع"])

        send_message(chat_id, "اختر الملف:", keyboard)
        return True


    # =========================
    # FILES (إرسال PDF)
    # =========================

    if current_state == "files":

        # 🔙 رجوع من الملفات
        if text == "🔙 رجوع":

            # إذا كنا داخل sub_subjects
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
    # EXAM FILE SELECT
    # =========================

    if current_state == "exam_file_select":

        # 🔙 رجوع من اختيار ملف الامتحان
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

                USER_STATE[chat_id + "_pdf"] = os.path.join(subject_path, file)
                USER_STATE[chat_id] = "exam_start_page"
                send_message(chat_id, "أدخل النطاق يدويًا")
                send_message(chat_id, "أدخل صفحة البداية:")
                return True

        return False


    return False

