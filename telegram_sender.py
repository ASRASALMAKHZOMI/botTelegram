import urllib.request
import urllib.parse
import json
import os
import requests   # ✅ أضفنا هذا فقط
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

            if keyboard and index == len(parts) - 1:
                payload["reply_markup"] = json.dumps({
                    "keyboard": keyboard,
                    "resize_keyboard": True
                })

            data = urllib.parse.urlencode(payload).encode()

            urllib.request.urlopen(url, data, timeout=15)

        except Exception as e:
            print("SEND MESSAGE ERROR:", e)


# =========================
# Remove Keyboard
# =========================

def remove_keyboard(chat_id, text):

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps({
                "remove_keyboard": True
            })
        }

        data = urllib.parse.urlencode(payload).encode()
        urllib.request.urlopen(url, data, timeout=15)

    except Exception as e:
        print("REMOVE KEYBOARD ERROR:", e)


# =========================
# Send File (FIXED فقط هنا 🔥)
# =========================

def send_file(chat_id, file_path):

    try:
        if not os.path.exists(file_path):
            print("FILE NOT FOUND:", file_path)
            return

        # حجم الملف
        file_size = os.path.getsize(file_path)
        print("Sending:", file_path)
        print("Size:", round(file_size / (1024*1024), 2), "MB")

        url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"

        # ❗ حماية (اختياري)
        if file_size > 50 * 1024 * 1024:
            print("FILE TOO LARGE")
            return

        # ✅ التعديل هنا فقط (stream بدل read)
        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                data={"chat_id": chat_id},
                files={"document": f},
                timeout=300
            )


    def edit_message(chat_id, message_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"

    requests.post(url, data={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    })


    def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"

    requests.post(url, data={
        "chat_id": chat_id,
        "message_id": message_id
    })
        print("Done:", response.status_code)

    except Exception as e:
        print("SEND FILE ERROR:", e)
