import os
from exam_module import generate_exam

LEVEL1_FOLDER = "Level 1"
LEVEL2_FOLDER = "Files"
LEVEL3_FOLDER = "Level 3"
LEVEL4_FOLDER = "Level 4"


def sort_by_number(items):
    return sorted(items)


def handle_exam_flow(chat_id, text, USER_STATE):

    # بدء النظام
    if USER_STATE.get(chat_id) == "exam_start":

        level_map = {
            "1": LEVEL1_FOLDER,
            "2": LEVEL2_FOLDER,
            "3": LEVEL3_FOLDER,
            "4": LEVEL4_FOLDER
        }

        if text in level_map:
            base_folder = level_map[text]

            subjects = [
                f for f in os.listdir(base_folder)
                if os.path.isdir(os.path.join(base_folder, f))
            ]

            USER_STATE[chat_id] = "exam_subject"
            USER_STATE[chat_id + "_base"] = base_folder
            USER_STATE[chat_id + "_subjects"] = subjects

            menu = "اختر المادة:\n\n"
            for i, s in enumerate(subjects, 1):
                menu += f"{i}- {s}\n"

            return menu

    # اختيار مادة
    if USER_STATE.get(chat_id) == "exam_subject":

        subjects = USER_STATE.get(chat_id + "_subjects", [])
        base = USER_STATE.get(chat_id + "_base")

        if text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(subjects):

                subject_path = os.path.join(base, subjects[index])
                files = [f for f in os.listdir(subject_path) if f.endswith(".pdf")]

                USER_STATE[chat_id] = "exam_pdf"
                USER_STATE[chat_id + "_files"] = files
                USER_STATE[chat_id + "_path"] = subject_path

                menu = "اختر الملزمة:\n\n"
                for i, f in enumerate(files, 1):
                    menu += f"{i}- {f}\n"

                return menu

    # اختيار PDF
    if USER_STATE.get(chat_id) == "exam_pdf":

        files = USER_STATE.get(chat_id + "_files", [])
        path = USER_STATE.get(chat_id + "_path")

        if text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(files):

                USER_STATE[chat_id] = "exam_start_page"
                USER_STATE[chat_id + "_pdf"] = os.path.join(path, files[index])

                return "أدخل صفحة البداية:"

    # صفحة البداية
    if USER_STATE.get(chat_id) == "exam_start_page":

        if text.isdigit():
            USER_STATE[chat_id + "_start"] = int(text)
            USER_STATE[chat_id] = "exam_end_page"
            return "أدخل صفحة النهاية:"

    # صفحة النهاية
    if USER_STATE.get(chat_id) == "exam_end_page":

        if text.isdigit():
            USER_STATE[chat_id + "_end"] = int(text)
            USER_STATE[chat_id] = "exam_type"

            return "اختر نوع الأسئلة:\n1- صح وخطأ\n2- اختيار من متعدد\n3- مقالي"

    # نوع الأسئلة
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

    # عدد الأسئلة
    if USER_STATE.get(chat_id) == "exam_count":

        if text.isdigit():

            pdf = USER_STATE.get(chat_id + "_pdf")
            start = USER_STATE.get(chat_id + "_start")
            end = USER_STATE.get(chat_id + "_end")
            qtype = USER_STATE.get(chat_id + "_type")
            count = int(text)

            USER_STATE[chat_id] = "main"

            return generate_exam(pdf, start, end, qtype, count)

    return None