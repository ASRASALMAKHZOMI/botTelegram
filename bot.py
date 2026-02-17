import urllib.request
import urllib.parse
import json
import time
import http.cookiejar
import re
import os

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
ENABLE_RESULTS = True        # False = إيقاف البحث
MAINTENANCE_MODE = False     # True = صيانة عامة
ADMIN_ID = "6829734732"      # رقمك لتجربة البوت أثناء الصيانة

FILES_FOLDER = "Files"
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

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }

    request = urllib.request.Request(url, data=body, headers=headers)
    urllib.request.urlopen(request)

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
        message += f"النسبة العامة: {marks[0]['Per']}%\n\n"

        message += "تفاصيل المواد:\n\n"

        for subject in marks:

            عملي = int(subject.get("t2", 0))
            اعمال = int(subject.get("t3", 0))
            المجموع = int(subject.get("t4", 0))
            الدرجة_الكلية = int(subject.get("maxDegree", 0))

            النهائي = المجموع - (عملي + اعمال)

            message += f"{subject['Subject']}\n"
            message += f"العملي: {عملي}\n"
            message += f"درجة الأعمال: {اعمال}\n"
            message += f"الامتحان النهائي: {نهائي}\n"
            message += f"الدرجة الكلية: {المجموع}\n"
            message += "-----------------\n"

        return message

    except Exception as e:
        return f"Error: {e}"

# =========================
# Sort Files
# =========================
def get_sorted_files(path):
    files = os.listdir(path)

    def extract_number(name):
        base = os.path.splitext(name)[0]
        first = base.split("-")[0]
        return int(first) if first.isdigit() else 999

    return sorted(files, key=extract_number)

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

            # ===== Maintenance Mode =====
            if MAINTENANCE_MODE and chat_id != ADMIN_ID:
                send_message(chat_id, "البوت متوقف حالياً للتحديث، حاول لاحقاً.")
                continue

            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"

            # ===== START =====
            if text == "/start":
                USER_STATE[chat_id] = "main"
                send_message(chat_id,
                    "القائمة الرئيسية:\n\n"
                    "1- الملازم\n"
                    "2- الجداول\n"
                    "3- البحث عن النتيجة\n"
                    "4- نبذة عني"
                )
                continue

            # ===== MAIN =====
            if USER_STATE[chat_id] == "main":

                if text == "3":
                    if not ENABLE_RESULTS:
                        send_message(chat_id, "خدمة النتائج متوقفة حالياً، قريباً بإذن الله.")
                        continue

                    USER_STATE[chat_id] = "search"
                    send_message(chat_id, "أرسل رقم القيد أو 0 للرجوع:")
                    continue

                elif text == "4":
                    send_message(chat_id,
                        "نبذة عني:\n\n"
                        "اسمي عبدالله المخزومي 👋\n"
                        "مطور هذا البوت لخدمة الطلاب وتسهيل الوصول للنتائج والملازم."
                    )
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- نبذة عني"
                    )
                    continue

            # ===== SEARCH =====
            if USER_STATE[chat_id] == "search":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة\n"
                        "4- نبذة عني"
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
                        "4- نبذة عني"
                    )
                else:
                    send_message(chat_id, "أدخل رقم صحيح أو 0 للرجوع.")

                continue

    except Exception as e:
        print("Error:", e)

    time.sleep(2)
