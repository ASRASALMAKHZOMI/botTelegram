import urllib.request
import urllib.parse
import json
import time
import re
import os
from ai_service import generate_challenge, evaluate_code
from exam_flow import handle_exam_flow

# =========================
# TOKEN
# =========================
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    print("ERROR: TOKEN not set.")
    exit()

# =========================
# CONTROL FLAGS
# =========================
MAINTENANCE_MODE = False
ADMIN_ID = "6829734732"

LEVEL1_FOLDER = "Level 1"
LEVEL2_FOLDER = "Files"
LEVEL3_FOLDER = "Level 3"
LEVEL4_FOLDER = "Level 4"

USER_STATE = {}

# =========================
# Send Message
# =========================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode()
    urllib.request.urlopen(url, data)

# =========================
# Send File
# =========================
def send_file(chat_id, file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"

    with open(file_path, "rb") as f:
        file_data = f.read()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{chat_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="{os.path.basename(file_path)}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    request = urllib.request.Request(url, data=body, headers=headers)
    urllib.request.urlopen(request)

# =========================
# Sort Function
# =========================
def sort_by_number(items):
    def extract_number(name):
        base = os.path.splitext(name)[0]
        match = re.match(r"(\d+)", base)
        if match:
            return int(match.group(1))
        return 999
    return sorted(items, key=extract_number)

def get_sorted_files(path):
    files = os.listdir(path)
    return sort_by_number(files)

# =========================
# MAIN LOOP
# =========================
print("Bot Started...")

last_update_id = 0

while True:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode("utf-8"))

        for update in data.get("result", []):

            last_update_id = update["update_id"]

            if "message" not in update:
                continue

            text = update["message"].get("text", "")
            chat_id = str(update["message"]["chat"]["id"])
            
            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"
            
            # ====== EXAM FLOW HANDLER ======
            response = handle_exam_flow(chat_id, text, USER_STATE)
            if response:
                send_message(chat_id, response)
                continue
            
            if MAINTENANCE_MODE and chat_id != ADMIN_ID:
                send_message(chat_id, "البوت متوقف حالياً للتحديث، حاول لاحقاً.")
                continue

            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"

            if text == "/start":
                USER_STATE[chat_id] = "main"
                send_message(chat_id,
                    "اهلًا بك،أختر ما تحتاجه:\n"
                    "1- الملازم\n"
                    "2- الجداول\n"
                    "3- تحدي البرمجة\n"
                    "4- توليد أسئلة امتحانية\n"
                    "5- من نحن"
                    )
                continue

            # =========================
            # MAIN MENU
            # =========================
            if USER_STATE[chat_id] == "main":

                if text == "1":
                    USER_STATE[chat_id] = "choose_level"
                    send_message(chat_id,
                    "اختر المستوى:\n\n"
                    "1- المستوى الأول\n"
                    "2- المستوى الثاني\n"
                    "3- المستوى الثالث\n"
                    "4- المستوى الرابع\n\n"
                    "0- رجوع"
                    )
                    continue

                elif text == "2":
                    send_message(chat_id, "سيتم إضافة الجداول قريباً.")
                    continue

                elif text == "3":
                    USER_STATE[chat_id] = "coding_level"
                    send_message(chat_id,
                        "اختر مستوى التحدي:\n\n"
                        "1- سهل\n"
                        "2- متوسط\n"
                        "3- صعب\n\n"
                        "0- رجوع"
                    )
                    continue

                elif text == "4":
                    USER_STATE[chat_id] = "exam_start"
                    send_message(chat_id,
                        "اختر المستوى:\n\n"
                        "1- المستوى الأول\n"
                        "2- المستوى الثاني\n"
                        "3- المستوى الثالث\n"
                        "4- المستوى الرابع"
                    )
                    continue
                
                elif text == "5":
                    send_message(chat_id,
                        "من نحن؟\n\n"
                        "اسمي عبدالله المخزومي 👋\n"
                        "مطور هذا البوت لخدمة الطلاب وتسهيل الوصول للملازم."
                    )
                    continue

            # =========================
            # LEVEL SELECTION
            # =========================
            if USER_STATE[chat_id] == "choose_level":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    continue

                if text == "1":
                    base_folder = LEVEL1_FOLDER
                elif text == "2":
                    base_folder = LEVEL2_FOLDER
                elif text == "3":
                    base_folder = LEVEL3_FOLDER
                elif text == "4":
                    base_folder = LEVEL4_FOLDER
                else:
                    send_message(chat_id, "اختيار غير صحيح.")
                    continue

                subjects = sort_by_number(
                    [f for f in os.listdir(base_folder)
                     if os.path.isdir(os.path.join(base_folder, f))]
                )

                USER_STATE[chat_id] = "subjects"
                USER_STATE[chat_id + "_subjects"] = subjects
                USER_STATE[chat_id + "_base_folder"] = base_folder

                menu = "المواد المتوفرة:\n\n"
                for i, subject in enumerate(subjects, 1):
                    menu += f"{i}- {subject}\n"

                menu += "\n0- رجوع"
                send_message(chat_id, menu)
                continue

            # =========================
            # SUBJECTS
            # =========================
            if USER_STATE[chat_id] == "subjects":
            
                if text == "0":
                    USER_STATE[chat_id] = "choose_level"
                    send_message(chat_id,
                        "اختر المستوى:\n\n"
                        "1- المستوى الأول\n"
                        "2- المستوى الثاني\n"
                        "3- المستوى الثالث\n"
                        "4- المستوى الرابع\n\n"
                        "0- رجوع"
                    )
                    continue
            
                subjects = USER_STATE.get(chat_id + "_subjects", [])
            
                if text.isdigit():
                    index = int(text) - 1
                    if 0 <= index < len(subjects):
            
                        base_folder = USER_STATE.get(chat_id + "_base_folder")
                        subject_path = os.path.join(base_folder, subjects[index])
            
                        # 🔥 نتحقق هل يوجد مجلدات داخلية
                        sub_subjects = [
                            f for f in os.listdir(subject_path)
                            if os.path.isdir(os.path.join(subject_path, f))
                        ]
            
                        # ✅ إذا يوجد مجلدات → ادخل sub_subjects
                        if sub_subjects:
            
                            USER_STATE[chat_id] = "sub_subjects"
                            USER_STATE[chat_id + "_sub_subjects"] = sub_subjects
                            USER_STATE[chat_id + "_subject_path"] = subject_path
            
                            menu = f"{subjects[index]}\n\n"
                            for i, sub in enumerate(sub_subjects, 1):
                                menu += f"{i}- {sub}\n"
            
                            menu += "\n0- رجوع"
                            send_message(chat_id, menu)
            
                        # ✅ إذا لا يوجد → اعرض الملفات مباشرة
                        else:
                            files = get_sorted_files(subject_path)
            
                            USER_STATE[chat_id] = "files"
                            USER_STATE[chat_id + "_path"] = subject_path
                            USER_STATE[chat_id + "_files"] = files
            
                            menu = f"{subjects[index]}\n\n"
                            for file in files:
                                menu += f"{os.path.splitext(file)[0]}\n"
            
                            menu += "\n0- رجوع"
                            send_message(chat_id, menu)
            
                    else:
                        send_message(chat_id, "رقم غير صحيح.")
            
                continue
            
            # =========================
            # SUB SUBJECTS
            # =========================
            if USER_STATE[chat_id] == "sub_subjects":
            
                if text == "0":
                    USER_STATE[chat_id] = "subjects"
            
                    subjects = USER_STATE.get(chat_id + "_subjects", [])
            
                    menu = "المواد المتوفرة:\n\n"
                    for i, subject in enumerate(subjects, 1):
                        menu += f"{i}- {subject}\n"
            
                    menu += "\n0- رجوع"
                    send_message(chat_id, menu)
            
                    continue
            
                sub_subjects = USER_STATE.get(chat_id + "_sub_subjects", [])
                subject_path = USER_STATE.get(chat_id + "_subject_path")
            
                if text.isdigit():
                    index = int(text) - 1
                    if 0 <= index < len(sub_subjects):
            
                        final_path = os.path.join(subject_path, sub_subjects[index])
                        files = get_sorted_files(final_path)
            
                        USER_STATE[chat_id] = "files"
                        USER_STATE[chat_id + "_path"] = final_path
                        USER_STATE[chat_id + "_files"] = files
            
                        menu = f"{sub_subjects[index]}\n\n"
                        for file in files:
                            menu += f"{os.path.splitext(file)[0]}\n"
            
                        menu += "\n0- رجوع"
                        send_message(chat_id, menu)
            
                    else:
                        send_message(chat_id, "رقم غير صحيح.")
            
                continue

            
            # =========================
            # FILES
            # =========================
            if USER_STATE[chat_id] == "files":
            
                if text == "0":
            
                    # إذا يوجد sub_subjects محفوظة → نرجع لها
                    if chat_id + "_sub_subjects" in USER_STATE:
                        USER_STATE[chat_id] = "sub_subjects"
            
                        sub_subjects = USER_STATE.get(chat_id + "_sub_subjects", [])
            
                        menu = "المواد المتوفرة:\n\n"
                        for i, sub in enumerate(sub_subjects, 1):
                            menu += f"{i}- {sub}\n"
            
                        menu += "\n0- رجوع"
                        send_message(chat_id, menu)
            
                    # إذا لا يوجد → نرجع للمواد الأساسية
                    else:
                        USER_STATE[chat_id] = "subjects"
            
                        subjects = USER_STATE.get(chat_id + "_subjects", [])
            
                        menu = "المواد المتوفرة:\n\n"
                        for i, subject in enumerate(subjects, 1):
                            menu += f"{i}- {subject}\n"
            
                        menu += "\n0- رجوع"
                        send_message(chat_id, menu)
            
                    continue
            
                subject_path = USER_STATE.get(chat_id + "_path")
                files = USER_STATE.get(chat_id + "_files", [])
            
                selected_file = None
            
                for file in files:
                    if os.path.splitext(file)[0].startswith(text):
                        selected_file = file
                        break
            
                if selected_file:
                    send_file(chat_id, os.path.join(subject_path, selected_file))
                else:
                    send_message(chat_id, "رقم غير صحيح.")
            
                continue


            # =========================
            # CODING CHALLENGE
            # =========================
            if USER_STATE[chat_id] == "coding_level":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    continue

                level_map = {
                    "1": "سهل",
                    "2": "متوسط",
                    "3": "صعب"
                }

                if text in level_map:
                    level = level_map[text]

                    send_message(chat_id, "جاري إنشاء التحدي...")
                    challenge = generate_challenge(level)

                    USER_STATE[chat_id] = "coding_wait_code"
                    USER_STATE[chat_id + "_challenge"] = challenge

                    send_message(chat_id, challenge)
                    send_message(chat_id, "💻 أرسل الكود الخاص بك الآن.")
                else:
                    send_message(chat_id, "اختيار غير صحيح.")

                continue

            if USER_STATE[chat_id] == "coding_wait_code":

                challenge = USER_STATE.get(chat_id + "_challenge")

                if not challenge:
                    USER_STATE[chat_id] = "main"
                    continue

                send_message(chat_id, "جاري تقييم الحل...")
                evaluation = evaluate_code(challenge, text)
                send_message(chat_id, evaluation)

                USER_STATE[chat_id] = "coding_level"
                USER_STATE.pop(chat_id + "_challenge", None)

                send_message(chat_id,
                    "اختر مستوى التحدي:\n\n"
                    "1- سهل\n"
                    "2- متوسط\n"
                    "3- صعب\n\n"
                    "0- رجوع"
                )
                
                continue

    except Exception as e:
        print("Error:", e)

    time.sleep(2)
