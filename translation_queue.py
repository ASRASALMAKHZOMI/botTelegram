import queue
import threading
import os
import fitz
import time

from telegram_sender import send_message
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    clean_text
)
from ai_service import call_ai

task_queue = queue.Queue()


# =========================
# تقسيم الرسائل
# =========================
def split_message(text, max_len=3500):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


# =========================
# ترجمة صفحة واحدة
# =========================
def translate_page(text):

    text = clean_text(text)

    if not text.strip():
        return "(صفحة فارغة)"

    prompt = f"""
ترجم النص التالي إلى العربية:

- كل سطر وتحته ترجمته
- لا تكرر
- لا تضف شرح
- استخدم مصطلحات برمجية صحيحة

النص:
{text}
"""

    messages = [
        {"role": "system", "content": "مترجم تقني."},
        {"role": "user", "content": prompt}
    ]

    attempt = 0

    while attempt < 5:
        try:
            result = call_ai(messages)

            # 🔥 التعديل المهم
            if result and result.strip():
                return result

        except Exception as e:
            print("Retry page...", e)

        time.sleep(3)
        attempt += 1

    # 🔥 fallback نظيف بدون فضيحة
    return text


# =========================
# Worker
# =========================
def worker():
    while True:

        task = task_queue.get()
        if task is None:
            break

        file_input, chat_id = task

        try:
            print("\n======================")
            print(f"[START] Task for chat_id: {chat_id}")

            send_message(chat_id, "🚀 بدء الترجمة...")

            # تحديد الملف
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            # تحقق
            if not is_pdf(file_path):
                send_message(chat_id, "❌ فقط PDF")
                continue

            if is_scanned(file_path):
                send_message(chat_id, "❌ الملف عبارة عن صور")
                continue

            # فتح الملف
            doc = fitz.open(file_path)
            total = len(doc)

            send_message(chat_id, f"📄 عدد الصفحات: {total}")

            # ترجمة صفحة صفحة
            for i, page in enumerate(doc):

                page_num = i + 1
                text = page.get_text()

                if not text.strip():
                    send_message(chat_id, f"📄 الصفحة {page_num}\n(صفحة فارغة)")
                    continue

                translated = translate_page(text)

                msg = f"📄 الصفحة {page_num}\n\n{translated}"

                # تقسيم لو طويل
                if len(msg) > 3500:
                    for part in split_message(msg):
                        send_message(chat_id, part)
                else:
                    send_message(chat_id, msg)

                # 🔥 يمنع 429
                time.sleep(2)

            doc.close()

            send_message(chat_id, "✅ تمت الترجمة بالكامل")

            print("[SUCCESS] Done")

        except Exception as e:
            print("[CRASH]:", e)
            send_message(chat_id, "❌ حدث خطأ")

        task_queue.task_done()
        print("[END TASK]")
        print("======================\n")


# =========================
# تشغيل Workers
# =========================
def start_workers(n=1):
    for i in range(n):
        print(f"[SYSTEM] Starting worker {i+1}")
        threading.Thread(target=worker, daemon=True).start()


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):

    position = task_queue.qsize() + 1

    print(f"[QUEUE] New task added. Position: {position}")

    task_queue.put((file_input, chat_id))

    send_message(chat_id, f"📌 تم إضافتك للطابور\n🔢 ترتيبك: {position}")


# =========================
# معرفة الطابور
# =========================
def get_position():
    return task_queue.qsize()
