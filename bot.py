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

        message = f"Student: {marks[0]['Name']}\n"
        message += f"Seat: {marks[0]['RegNo']}\n"
        message += f"Percentage: {marks[0]['Per']}%\n\n"

        for subject in marks:
            message += f"{subject['Subject']}: {subject['t4']}\n"

        return message

    except Exception as e:
        return f"Error: {e}"


# =========================
# Sort Files by Number
# =========================
def get_sorted_files(path):
    files = os.listdir(path)

    def extract_number(name):
        base = os.path.splitext(name)[0]
        first_part = base.split("-")[0]
        return int(first_part) if first_part.isdigit() else 999

    return sorted(files, key=extract_number)


# =========================
# Main Loop
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

            # ================= START =================
            if text == "/start":
                USER_STATE[chat_id] = "main"
                send_message(chat_id,
                    "القائمة الرئيسية:\n\n"
                    "1- الملازم\n"
                    "2- الجداول\n"
                    "3- البحث عن النتيجة"
                )
                continue

            # ================= MAIN =================
            if USER_STATE[chat_id] == "main":

                if text == "1":
                    subjects = [
                        f for f in os.listdir(FILES_FOLDER)
                        if os.path.isdir(os.path.join(FILES_FOLDER, f))
                    ]

                    if not subjects:
                        send_message(chat_id, "لا توجد مواد حالياً.")
                        continue

                    USER_STATE[chat_id] = "subjects"

                    menu = "المواد المتوفرة:\n\n"
                    for i, subject in enumerate(subjects, 1):
                        menu += f"{i}- {subject}\n"

                    menu += "\n0- رجوع"
                    send_message(chat_id, menu)
                    continue

                elif text == "2":
                    send_message(chat_id, "الجداول سيتم إضافتها قريباً.")
                    continue

                elif text == "3":
                    USER_STATE[chat_id] = "search"
                    send_message(chat_id, "أرسل رقم القيد أو 0 للرجوع:")
                    continue

            # ================= SUBJECTS =================
            if USER_STATE[chat_id] == "subjects":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة"
                    )
                    continue

                subjects = [
                    f for f in os.listdir(FILES_FOLDER)
                    if os.path.isdir(os.path.join(FILES_FOLDER, f))
                ]

                if text.isdigit():
                    index = int(text) - 1
                    if 0 <= index < len(subjects):

                        subject_path = os.path.join(FILES_FOLDER, subjects[index])
                        files = get_sorted_files(subject_path)

                        if not files:
                            send_message(chat_id, "لا توجد ملازم.")
                            continue

                        USER_STATE[chat_id] = "files"
                        USER_STATE[chat_id + "_path"] = subject_path

                        menu = f"{subjects[index]}\n\n"
                        for file in files:
                            menu += f"{os.path.splitext(file)[0]}\n"

                        menu += "\n0- رجوع"
                        send_message(chat_id, menu)
                    else:
                        send_message(chat_id, "رقم غير صحيح.")
                continue

            # ================= FILES =================
            if USER_STATE[chat_id] == "files":

                if text == "0":
                    USER_STATE[chat_id] = "subjects"

                    subjects = [
                        f for f in os.listdir(FILES_FOLDER)
                        if os.path.isdir(os.path.join(FILES_FOLDER, f))
                    ]

                    menu = "المواد المتوفرة:\n\n"
                    for i, subject in enumerate(subjects, 1):
                        menu += f"{i}- {subject}\n"

                    menu += "\n0- رجوع"
                    send_message(chat_id, menu)
                    continue

                subject_path = USER_STATE.get(chat_id + "_path")
                files = get_sorted_files(subject_path)

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

            # ================= SEARCH =================
            if USER_STATE[chat_id] == "search":

                if text == "0":
                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة"
                    )
                    continue

                if text.isdigit():
                    send_message(chat_id, "Checking...")
                    result_text = get_student_result(text)
                    send_message(chat_id, result_text)

                    USER_STATE[chat_id] = "main"
                    send_message(chat_id,
                        "القائمة الرئيسية:\n\n"
                        "1- الملازم\n"
                        "2- الجداول\n"
                        "3- البحث عن النتيجة"
                    )
                else:
                    send_message(chat_id, "أدخل رقم صحيح أو 0 للرجوع.")

                continue

    except Exception as e:
        print("Error:", e)

    time.sleep(2)
