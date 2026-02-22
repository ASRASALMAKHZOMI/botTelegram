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
def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = json.dumps({
            "keyboard": keyboard,
            "resize_keyboard": True
        })

    data = urllib.parse.urlencode(payload).encode()
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

                if isinstance(response, dict):
                    send_message(chat_id, response["text"], response.get("keyboard"))
                else:
                    send_message(chat_id, response)
            
                if chat_id + "_exam_ready" in USER_STATE:
                    from exam_module import generate_exam
                
                    pdf, start, end, qtype, count = USER_STATE.pop(chat_id + "_exam_ready")
                
                    result = generate_exam(pdf, start, end, qtype, count)
                
                    send_message(chat_id, result)
                
                    # تنظيف جميع متغيرات الامتحان
                    USER_STATE.pop(chat_id + "_exam_mode", None)
                    USER_STATE.pop(chat_id + "_start", None)
                    USER_STATE.pop(chat_id + "_end", None)
                    USER_STATE.pop(chat_id + "_type", None)
                    USER_STATE.pop(chat_id + "_pdf", None)
                
                    # رجوع فعلي للقائمة الرئيسية
                    USER_STATE[chat_id] = "main"
                
                    keyboard = [
                        ["📚 الملازم", "📊 الجداول"],
                        ["💻 تحدي البرمجة", "📝 توليد أسئلة امتحانية"],
                        ["👤 من نحن"]
                    ]
                
                    send_message(chat_id, "تم إرجاعك للقائمة الرئيسية.", keyboard)
                
                continue
                   
            
               
            
            if MAINTENANCE_MODE and chat_id != ADMIN_ID:
                send_message(chat_id, "البوت متوقف حالياً للتحديث، حاول لاحقاً.")
                continue

            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"

            if text == "/start":
                USER_STATE[chat_id] = "main"
                USER_STATE.pop(chat_id + "_exam_mode", None)
            
                keyboard = [
                    ["📚 الملازم", "📊 الجداول"],
                    ["💻 تحدي البرمجة", "📝 توليد أسئلة امتحانية"],
                    ["👤 من نحن"]
                ]
            
                send_message(chat_id, "اهلًا بك، اختر ما تحتاجه:", keyboard)
                continue
        
            # =========================
            # MAIN MENU
            # =========================
            if USER_STATE[chat_id] == "main":

                if text == "📚 الملازم":
                    USER_STATE[chat_id] = "choose_level"
                
                    keyboard = [
                        ["📘 المستوى الأول"],
                        ["📗 المستوى الثاني"],
                        ["📙 المستوى الثالث"],
                        ["📕 المستوى الرابع"],
                        ["🔙 /start"]
                    ]
                
                    send_message(chat_id, "اختر المستوى:", keyboard)
                    continue

                elif text == "📊 الجداول":
                    send_message(chat_id, "سيتم إضافة الجداول قريباً.")
                    continue

                elif text == "💻 تحدي البرمجة":
                   USER_STATE[chat_id] = "coding_level"

                   keyboard = [
                       ["🟢 سهل"],
                       ["🟡 متوسط"],
                       ["🔴 صعب"],
                       ["🔙 رجوع"]
                   ]

                   send_message(chat_id, "اختر مستوى التحدي:", keyboard)
                   continue

                elif text == "📝 توليد أسئلة امتحانية":
                       USER_STATE[chat_id] = "choose_level"
                       USER_STATE[chat_id + "_exam_mode"] = True

                       keyboard = [
                           ["📘 المستوى الأول"],
                           ["📗 المستوى الثاني"],
                           ["📙 المستوى الثالث"],
                           ["📕 المستوى الرابع"],
                           ["🔙 /start"]
                       ]

                       send_message(chat_id, "اختر المستوى:", keyboard)
                       continue
                
                elif text == "👤 من نحن":
                    send_message(chat_id,
                        "من نحن؟\n\n"
                        "اسمي عبدالله المخزومي 👋\n"
                        "مطور هذا البوت لخدمة الطلاب وتسهيل الوصول للملازم."
                    )
                    continue

            # =========================
            # LEVEL SELECTION
            # =========================
            if USER_STATE[chat_id] in ["choose_level", "choose_level_exam"]:

                if text == "📘 المستوى الأول":
                    base_folder = LEVEL1_FOLDER
                elif text == "📗 المستوى الثاني":
                    base_folder = LEVEL2_FOLDER
                elif text == "📙 المستوى الثالث":
                    base_folder = LEVEL3_FOLDER
                elif text == "📕 المستوى الرابع":
                    base_folder = LEVEL4_FOLDER
                elif text == "🔙 /start":
                    USER_STATE[chat_id] = "main"
                    continue
                else:
                    send_message(chat_id, "اختيار غير صحيح.")
                    continue

                subjects = sort_by_number(
                    [f for f in os.listdir(base_folder)
                     if os.path.isdir(os.path.join(base_folder, f))]
                )

                if USER_STATE.get(chat_id + "_exam_mode"):
                    USER_STATE[chat_id] = "exam_subject"
                else:
                    USER_STATE[chat_id] = "subjects"
                
                USER_STATE[chat_id + "_subjects"] = subjects
                USER_STATE[chat_id + "_base_folder"] = base_folder

                keyboard = []

                for subject in subjects:
                    keyboard.append([subject])
                
                keyboard.append(["🔙 رجوع"])
                
                send_message(chat_id, "المواد المتوفرة:", keyboard)

                continue

          
            # =========================
            # SUBJECTS
            # =========================
            if USER_STATE[chat_id] in ["subjects", "exam_subject"]:
            
                # 🔙 رجوع
                if text == "🔙 رجوع":
                    USER_STATE[chat_id] = "choose_level"
            
                    keyboard = [
                        ["📘 المستوى الأول"],
                        ["📗 المستوى الثاني"],
                        ["📙 المستوى الثالث"],
                        ["📕 المستوى الرابع"],
                        ["🔙 /start"]
                    ]
            
                    send_message(chat_id, "اختر المستوى:", keyboard)
                    continue
            
                subjects = USER_STATE.get(chat_id + "_subjects", [])
            
                if text in subjects:
            
                    base_folder = USER_STATE.get(chat_id + "_base_folder")
                    subject_path = os.path.join(base_folder, text)
            
                    sub_subjects = [
                        f for f in os.listdir(subject_path)
                        if os.path.isdir(os.path.join(subject_path, f))
                    ]
            
                    # لو فيه مجلدات فرعية
                    if sub_subjects:
            
                        USER_STATE[chat_id] = "sub_subjects"
                        USER_STATE[chat_id + "_sub_subjects"] = sub_subjects
                        USER_STATE[chat_id + "_subject_path"] = subject_path
            
                        keyboard = [[s] for s in sub_subjects]
                        keyboard.append(["🔙 رجوع"])
            
                        send_message(chat_id, text, keyboard)
            
                    # لو ما فيه مجلدات → نعرض الملفات
                    else:
            
                        files = get_sorted_files(subject_path)
            
                        # 🔥 هنا التعديل الصحيح
                        if USER_STATE.get(chat_id + "_exam_mode"):
                            USER_STATE[chat_id] = "exam_file_select"
                        else:
                            USER_STATE[chat_id] = "files"
            
                        USER_STATE[chat_id + "_path"] = subject_path
                        USER_STATE[chat_id + "_files"] = files
                        USER_STATE[chat_id + "_subject_path"] = subject_path
            
                        keyboard = [[os.path.splitext(f)[0]] for f in files]
                        keyboard.append(["🔙 رجوع"])
            
                        send_message(chat_id, text, keyboard)
            
                else:
                    send_message(chat_id, "اختيار غير صحيح.")
            
                continue
                        
            # =========================
            # SUB SUBJECTS
            # =========================
            if USER_STATE[chat_id] in ["sub_subjects", "exam_sub_subjects"]:
            
                if text == "🔙 رجوع":
                    USER_STATE[chat_id] = "subjects"
            
                    subjects = USER_STATE.get(chat_id + "_subjects", [])
            
                    keyboard = []
                    for subject in subjects:
                        keyboard.append([subject])
            
                    keyboard.append(["🔙 رجوع"])
            
                    send_message(chat_id, "المواد المتوفرة:", keyboard)
                    continue
            
                sub_subjects = USER_STATE.get(chat_id + "_sub_subjects", [])
                subject_path = USER_STATE.get(chat_id + "_subject_path")
            
                if text in sub_subjects:
            
                    final_path = os.path.join(subject_path, text)
                    files = get_sorted_files(final_path)
            
                    USER_STATE[chat_id] = "files"
                    USER_STATE[chat_id + "_path"] = final_path
                    USER_STATE[chat_id + "_files"] = files
            
                    keyboard = []
                    for file in files:
                        keyboard.append([os.path.splitext(file)[0]])
            
                    keyboard.append(["🔙 رجوع"])
            
                    send_message(chat_id, f"{text}", keyboard)
            
                else:
                    send_message(chat_id, "اختيار غير صحيح.")
            
                continue

            # =========================
            # EXAM FILE SELECT
            # =========================
            if USER_STATE[chat_id] == "exam_file_select":

                subject_path = USER_STATE.get(chat_id + "_subject_path")
                files = USER_STATE.get(chat_id + "_files", [])
            
                for file in files:
                    if text == os.path.splitext(file)[0]:
                        USER_STATE[chat_id + "_pdf"] = os.path.join(subject_path, file)
                        USER_STATE[chat_id] = "exam_start_page"
                        send_message(chat_id, "أدخل النطاق يدويًا")

                        send_message(chat_id, "أدخل صفحة البداية:")
                        break
                else:
                    send_message(chat_id, "اختيار غير صحيح.")
            
                continue
            # =========================
            # FILES
            # =========================

            if USER_STATE[chat_id] == "files":
            
                if text == "🔙 رجوع":
            
                    if chat_id + "_sub_subjects" in USER_STATE:
                        USER_STATE[chat_id] = "sub_subjects"
                        sub_subjects = USER_STATE.get(chat_id + "_sub_subjects", [])
            
                        keyboard = []
                        for sub in sub_subjects:
                            keyboard.append([sub])
            
                        keyboard.append(["🔙 رجوع"])
            
                        send_message(chat_id, "اختر:", keyboard)
            
                    else:
                        USER_STATE[chat_id] = "subjects"
                        subjects = USER_STATE.get(chat_id + "_subjects", [])
            
                        keyboard = []
                        for subject in subjects:
                            keyboard.append([subject])
            
                        keyboard.append(["🔙 رجوع"])
            
                        send_message(chat_id, "المواد المتوفرة:", keyboard)
            
                    continue
            
                subject_path = USER_STATE.get(chat_id + "_path")
                files = USER_STATE.get(chat_id + "_files", [])
            
                for file in files:
                    if text == os.path.splitext(file)[0]:
                        send_file(chat_id, os.path.join(subject_path, file))
                        break
                else:
                    send_message(chat_id, "اختيار غير صحيح.")
            
                continue

            # =========================
            # CODING CHALLENGE
            # =========================
            if USER_STATE[chat_id] == "coding_level":
            
                if text == "🔙 رجوع":
                    USER_STATE[chat_id] = "main"
            
                    keyboard = [
                        ["📚 الملازم", "📊 الجداول"],
                        ["💻 تحدي البرمجة", "📝 توليد أسئلة امتحانية"],
                        ["👤 من نحن"]
                    ]
            
                    send_message(chat_id, "اهلًا بك، اختر ما تحتاجه:", keyboard)
                    continue
            
                level_map = {
                    "🟢 سهل": "سهل",
                    "🟡 متوسط": "متوسط",
                    "🔴 صعب": "صعب"
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

                keyboard = [
                    ["🟢 سهل"],
                    ["🟡 متوسط"],
                    ["🔴 صعب"],
                    ["🔙 رجوع"]
                ]
                
                send_message(chat_id, "اختر مستوى التحدي:", keyboard)
                
    except Exception as e:
        print("Error:", e)

    time.sleep(2)
