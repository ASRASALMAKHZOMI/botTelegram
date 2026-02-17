import urllib.request
import urllib.parse
import json
import time
import http.cookiejar
import re
import os

# =========================
# TOKEN from Environment
# =========================
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    print("ERROR: TOKEN not set in environment variables.")
    exit()

# =========================
# Allowed Users
# =========================
ALLOWED_USERS = [
    "6829734732",
    "6560246421"
]

FILES_FOLDER = "Files"
USER_STATE = {}

# =========================
# Send Telegram Message
# =========================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode()

    try:
        urllib.request.urlopen(url, data)
    except Exception as e:
        print("Send error:", e)


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
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

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

        request = urllib.request.Request(url, data=post_data, headers=headers, method="POST")
        response = opener.open(request)
        result = json.loads(response.read().decode("utf-8"))

        if result.get("status") != "1":
            return "No result found."

        data = result["data"]
        marks = data["marks"]

        message = f"Student: {marks[0]['Name']}\n"
        message += f"Seat: {marks[0]['RegNo']}\n"
        message += f"Percentage: {marks[0]['Per']}%\n\n"

        for subject in marks:
            message += f"{subject['Subject']}: {subject['t4']}\n"

        return message

    except Exception as e:
        return f"Error occurred: {e}"


# =========================
# Main Polling Loop
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

            if chat_id not in ALLOWED_USERS:
                send_message(chat_id, "Not authorized.")
                continue

            if chat_id not in USER_STATE:
                USER_STATE[chat_id] = "main"

            # ================= MAIN MENU =================
            if text == "/start":
                USER_STATE[chat_id] = "main"
                send_message(chat_id,
                    "مرحباً بك 👋\n\n"
                    "1- الملازم\n"
                    "2- البحث عن النتيجة"
                )
                continue

            # ================= MAIN =================
            if USER_STATE[chat_id] == "main":

                if text == "1":
                    subjects = [
                        folder for folder in os.listdir(FILES_FOLDER)
                        if os.path.isdir(os.path.join(FILES_FOLDER, folder))
                    ]

                    if not subjects:
                        send_message(chat_id, "لا توجد مواد حالياً.")
                        continue

                    USER_STATE[chat_id] = "subjects"

                    menu = "المواد المتوفرة:\n\n"
                    for i, subject in enumerate(subjects, 1):
                        menu += f"{i}- {subject}\n"

                    menu += "\nأرسل رقم المادة."
                    send_message(chat_id, menu)
                    continue

                elif text == "2":
                    USER_STATE[chat_id] = "search"
                    send_message(chat_id, "أرسل رقم القيد:")
                    continue

            # ================= SUBJECTS =================
            if USER_STATE[chat_id] == "subjects":

                subjects = [
                    folder for folder in os.listdir(FILES_FOLDER)
                    if os.path.isdir(os.path.join(FILES_FOLDER, folder))
                ]

                if text.isdigit():
                    index = int(text) - 1
                    if 0 <= index < len(subjects):

                        subject_name = subjects[index]
                        subject_path = os.path.join(FILES_FOLDER, subject_name)

                        files = os.listdir(subject_path)

                        if not files:
                            send_message(chat_id, "لا توجد ملازم في هذه المادة.")
                            continue

                        USER_STATE[chat_id] = "files"
                        USER_STATE[chat_id + "_path"] = subject_path

                        menu = f"{subject_name}\n\n"
                        for i, file in enumerate(files, 1):
                            menu += f"{i}- {file}\n"

                        menu += "\nأرسل رقم الملزمة."
                        send_message(chat_id, menu)

                    else:
                        send_message(chat_id, "رقم غير صحيح.")
                else:
                    send_message(chat_id, "اختر رقم صحيح.")
                continue

            # ================= FILES =================
            if USER_STATE[chat_id] == "files":

                subject_path = USER_STATE.get(chat_id + "_path")
                files = os.listdir(subject_path)

                if text.isdigit():
                    index = int(text) - 1
                    if 0 <= index < len(files):
                        file_path = os.path.join(subject_path, files[index])
                        send_file(chat_id, file_path)
                    else:
                        send_message(chat_id, "رقم غير صحيح.")
                else:
                    send_message(chat_id, "اختر رقم صحيح.")
                continue

            # ================= SEARCH =================
            if USER_STATE[chat_id] == "search":

                if text.isdigit():
                    send_message(chat_id, "Checking...")
                    result_text = get_student_result(text)
                    send_message(chat_id, result_text)
                    USER_STATE[chat_id] = "main"
                else:
                    send_message(chat_id, "أدخل رقم قيد صحيح.")
                continue

    except Exception as e:
        print("Main loop error:", e)

    time.sleep(2)
