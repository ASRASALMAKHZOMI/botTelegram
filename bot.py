import urllib.request
import urllib.parse
import json
import time
import http.cookiejar
import re
import os
from ai_service import generate_challenge, evaluate_code


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
ENABLE_RESULTS = False
MAINTENANCE_MODE = True
ADMIN_ID = "6829734732"

LEVEL1_FOLDER = "Level 1"
LEVEL2_FOLDER = "Files"
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
# Get Student Result
# =========================
def get_student_result(seat_number):

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj)
    )

    try:
        page = opener.open("https://seiyunu.edu.ye/Home/keyIn")
        html = page.read().decode("utf-8")

        token_match = re.search(
            r'name="__RequestVerificationToken".*?value="(.+?)"',
            html
        )

        if not token_match:
            return "Token not found."

        token = token_match.group(1)

        post_data = urllib.parse.urlencode({
            "__RequestVerificationToken": token,
            "userID": seat_number
        }).encode("utf-8")

        url = f"https://seiyunu.edu.ye/Students/Results/findResultByRegNo/{seat_number}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://seiyunu.edu.ye/Home/keyIn",
            "Origin": "https://seiyunu.edu.ye"
        }

        request = urllib.request.Request(
            url, data=post_data, headers=headers, method="POST"
        )

        response = opener.open(request)
        result = json.loads(response.read().decode("utf-8"))

        if result.get("status") != "1":
            return "No result found."

        data = result["data"]
        marks = data["marks"]

        message = f"الطالب: {marks[0]['Name']}\n"
        message += f"رقم القيد: {marks[0]['RegNo']}\n"
        message += f"التخصص: {data['SpecialistName']}\n"
        message += f"المستوى: {data['LevelName']}\n"
        message += f"الكلية: {data['CollegetName']}\n"
        message += f"النسبة: {marks[0]['Per']}%\n\n"

        message += "تفاصيل المواد:\n\n"

        for subject in marks:
            practical = int(subject.get("t0", 0))
            coursework = int(subject.get("t2", 0))
            final_exam = int(subject.get("t3", 0))
            total = int(subject.get("t4", 0))
            max_degree = int(subject.get("maxDegree", 0))

            message += f"{subject['Subject']}\n"
            message += f"العملي: {practical}\n"
            message += f"أعمال الفصل: {coursework}\n"
            message += f"الامتحان النهائي: {final_exam}\n"
            message += f"الدرجة الكلية: {total} / {max_degree}\n"
            message += "-----------------\n"

        return message

    except Exception as e:
        return f"Error: {e}"

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

            if MAINTENANCE_MODE and chat_id != ADMIN_ID:
                send_message(chat_id, "البوت متوقف حالياً للتحديث، حاول لاحقاً.")
                continue

            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"

            if text == "/start":
                USER_STATE[chat_id] = "main"
                send_message(chat_id,
                    "1- الملازم\n"
                    "2- الجداول\n"
                    "3- البحث عن النتيجة\n"
                    "4- تحدي البرمجة\n"
                    "5- من نحن"

                )
                continue

            if USER_STATE[chat_id] == "main":

                if text == "1":
                    USER_STATE[chat_id] = "choose_level"
                    send_message(chat_id,
                        "اختر المستوى:\n\n"
                        "1- المستوى الأول\n"
                        "2- المستوى الثاني\n\n"
                        "0- رجوع"
                    )
                    continue

                elif text == "2":
                    send_message(chat_id, "سيتم إضافة الجداول قريباً.")
                    continue

                elif text == "3":

                    if not ENABLE_RESULTS:
                        send_message(chat_id, "خدمة النتائج متوقفة حالياً.")
                        continue

                    USER_STATE[chat_id] = "search"
                    send_message(chat_id, "أرسل رقم القيد أو 0 للرجوع:")
                    continue

                elif text == "4":
                    USER_STATE[chat_id] = "coding_level"
                    send_message(chat_id,
                        "اختر مستوى التحدي:\n\n"
                        "1- سهل\n"
                        "2- متوسط\n"
                        "3- صعب\n\n"
                        "0- رجوع"
                    )
                    continue

                elif text == "5":
                    send_message(chat_id,
                        "من نحن؟\n\n"
                        "اسمي عبدالله المخزومي 👋\n"
                        "مطور هذا البوت لخدمة الطلاب وتسهيل الوصول للملازم والنتائج."
                    )

                    USER_STATE[chat_id] = "main"

                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- تحدي البرمجة\n"
                        "5- من نحن"
                    )
                    continue



            if USER_STATE[chat_id] == "choose_level":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- تحدي البرمجة\n"
                        "5- من نحن"
                    )
                    continue

                if text == "1":
                    base_folder = LEVEL1_FOLDER
                elif text == "2":
                    base_folder = LEVEL2_FOLDER
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

            if USER_STATE[chat_id] == "subjects":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id, "اكتب /start للعودة للقائمة الرئيسية.")
                    continue

                subjects = USER_STATE.get(chat_id + "_subjects", [])

                if text.isdigit():
                    index = int(text) - 1
                    if 0 <= index < len(subjects):

                        base_folder = USER_STATE.get(chat_id + "_base_folder")
                        subject_path = os.path.join(base_folder, subjects[index])
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

            if USER_STATE[chat_id] == "files":

                if text == "0":
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
            # CODING CHALLENGE - اختيار المستوى
            # =========================
            if USER_STATE[chat_id] == "coding_level":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- تحدي البرمجة\n"
                        "5- من نحن"
                    )
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


            # =========================
            # CODING CHALLENGE - انتظار الكود
            # =========================
            if USER_STATE[chat_id] == "coding_wait_code":

                challenge = USER_STATE.get(chat_id + "_challenge")

                if not challenge:
                    USER_STATE[chat_id] = "main"
                    continue

                send_message(chat_id, "جاري تقييم الحل...")

                evaluation = evaluate_code(challenge, text)

                send_message(chat_id, evaluation)

                USER_STATE[chat_id] = "main"
                USER_STATE.pop(chat_id + "_challenge", None)

                send_message(chat_id,
                    "القائمة الرئيسية:\n\n"
                    "1- الملازم\n"
                    "2- الجداول\n"
                    "3- البحث عن النتيجة\n"
                    "4- تحدي البرمجة\n"
                    "5- من نحن"
                )

                continue

            if USER_STATE[chat_id] == "search":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- تحدي البرمجة\n"
                        "5- من نحن"
                    )
                    continue

                if text.isdigit():
                    send_message(chat_id, "Checking...")
                    result = get_student_result(text)
                    send_message(chat_id, result)

                    USER_STATE[chat_id] = "main"

                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- تحدي البرمجة\n"
                        "5- من نحن"
                    )
                else:
                    send_message(chat_id, "أدخل رقم صحيح.")

                continue

    except Exception as e:
        print("Error:", e)

    time.sleep(2)


