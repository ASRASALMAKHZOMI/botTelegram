import urllib.request
import urllib.parse
import json
import os
from config import TOKEN

# =========================
# Send Message
# =========================

def send_message(chat_id, text, keyboard=None):

    MAX_LENGTH = 4000

    def split_text(text):
        return [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]

    parts = split_text(text)

    for index, part in enumerate(parts):
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

            payload = {
                "chat_id": chat_id,
                "text": part
            }

            # فقط في آخر رسالة أعد الكيبورد
            if keyboard and index == len(parts) - 1:
                payload["reply_markup"] = json.dumps({
                    "keyboard": keyboard,
                    "resize_keyboard": True
                })

            data = urllib.parse.urlencode(payload).encode()
            urllib.request.urlopen(url, data, timeout=20)

        except Exception as e:
            print("SEND ERROR:", e)

# =========================
# Remove Keyboard
# =========================

def remove_keyboard(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps({
            "remove_keyboard": True
        })
    }

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
