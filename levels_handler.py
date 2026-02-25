import os
from state import USER_STATE
from config import LEVEL1_FOLDER, LEVEL2_FOLDER, LEVEL3_FOLDER, LEVEL4_FOLDER
from telegram_sender import send_message
from file_service import sort_by_number, get_subdirectories


# =========================
# Levels & Subjects Handler
# =========================

def handle_levels(chat_id, text):

    current_state = USER_STATE.get(chat_id)

    # =========================
    # LEVEL SELECTION
    # =========================

    if current_state in ["choose_level"]:

        if text == "📘 المستوى الأول":
            base_folder = LEVEL1_FOLDER
        elif text == "📗 المستوى الثاني":
            base_folder = LEVEL2_FOLDER
        elif text == "📙 المستوى الثالث":
            base_folder = LEVEL3_FOLDER
        elif text == "📕 المستوى الرابع":
            base_folder = LEVEL4_FOLDER
        elif text == "/start":
            USER_STATE[chat_id] = "main"
            return False
        else:
            return False

        # جلب المواد (المجلدات داخل المستوى)
        subjects = sort_by_number(get_subdirectories(base_folder))

        # تحديد هل نحن في وضع امتحان أم لا
        if USER_STATE.get(chat_id + "_exam_mode"):
            USER_STATE[chat_id] = "exam_subject"
        else:
            USER_STATE[chat_id] = "subjects"

        USER_STATE[chat_id + "_subjects"] = subjects
        USER_STATE[chat_id + "_base_folder"] = base_folder

        keyboard = [[subject] for subject in subjects]
        keyboard.append(["🔙 رجوع"])

        send_message(chat_id, "المواد المتوفرة:", keyboard)
        return True


    # =========================
    # SUBJECTS
    # =========================

    if current_state in ["subjects", "exam_subject"]:

        if text == "🔙 رجوع":
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

        subjects = USER_STATE.get(chat_id + "_subjects", [])

        if text not in subjects:
            return False

        base_folder = USER_STATE.get(chat_id + "_base_folder")
        subject_path = os.path.join(base_folder, text)

        sub_subjects = get_subdirectories(subject_path)

        # لو فيه مجلدات فرعية
        if sub_subjects:

            USER_STATE[chat_id] = "sub_subjects"
            USER_STATE[chat_id + "_sub_subjects"] = sub_subjects
            USER_STATE[chat_id + "_subject_path"] = subject_path

            keyboard = [[s] for s in sub_subjects]
            keyboard.append(["🔙 رجوع"])

            send_message(chat_id, text, keyboard)
            return True

        # لو ما فيه → ننتقل للملفات (سيكملها files_handler)
        USER_STATE[chat_id + "_subject_path"] = subject_path
        return False


    # =========================
    # SUB SUBJECTS
    # =========================

    if current_state in ["sub_subjects"]:

        if text == "🔙 رجوع":
            USER_STATE[chat_id] = "subjects"

            subjects = USER_STATE.get(chat_id + "_subjects", [])
            keyboard = [[subject] for subject in subjects]
            keyboard.append(["🔙 رجوع"])

            send_message(chat_id, "المواد المتوفرة:", keyboard)
            return True

        sub_subjects = USER_STATE.get(chat_id + "_sub_subjects", [])

        if text not in sub_subjects:
            return False

        subject_path = USER_STATE.get(chat_id + "_subject_path")
        final_path = os.path.join(subject_path, text)

        USER_STATE[chat_id + "_subject_path"] = final_path

        # نترك عرض الملفات لـ files_handler
        return False


    return False