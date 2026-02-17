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
        message += f"Level: {data['LevelName']}\n"
        message += f"Specialization: {data['SpecialistName']}\n"
        message += f"College: {data['CollegetName']}\n"
        message += f"Percentage: {marks[0]['Per']}%\n\n"
        message += "Subjects:\n"

        for subject in marks:
            message += f"- {subject['Subject']}: {subject['t4']}\n"

        return message

    except Exception as e:
        return f"Error occurred: {e}"


# =========================
# Polling Loop
# =========================
print("Bot started on Render...")

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

            if text == "/start":
                send_message(chat_id, "Send seat number to get result.")
                continue

            if text.isdigit():
                send_message(chat_id, "Checking...")
                result_text = get_student_result(text)
                send_message(chat_id, result_text)
            else:
                send_message(chat_id, "Send valid seat number.")

    except Exception as e:
        print("Main loop error:", e)

    time.sleep(2)

