import queue
import threading
import os

from telegram_sender import send_message, send_file
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    translate_pdf
)

task_queue = queue.Queue()


def worker():
    while True:

        task = task_queue.get()

        if task is None:
            break

        file_input, chat_id = task

        try:
            # 🔥 نخبره أنه بدأ دوره
            send_message(chat_id, "🚀 جاء دورك الآن، جاري بدء الترجمة...")

            # تحديد نوع الملف
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            if not is_pdf(file_path):
                send_message(chat_id, "❌ فقط PDF مدعوم")
                continue

            if is_scanned(file_path):
                send_message(chat_id, "❌ الملف ممسوح (صور) غير مدعوم")
                continue

            send_message(chat_id, "⏳ جاري الترجمة...")

            output = translate_pdf(file_path)

            send_file(chat_id, output)

        except Exception as e:
            print("Translation Error:", e)
            send_message(chat_id, "❌ حدث خطأ أثناء الترجمة")

        task_queue.task_done()


def start_workers(n=2):
    for _ in range(n):
        threading.Thread(target=worker, daemon=True).start()


def add_task(file_input, chat_id):

    # 🔥 نحسب ترتيبه قبل الإضافة
    position = task_queue.qsize() + 1

    task_queue.put((file_input, chat_id))

    # 🔥 نرسل له ترتيبه
    send_message(chat_id, f"📌 تم إضافتك للطابور\n🔢 ترتيبك: {position}")


def get_position():
    return task_queue.qsize()
