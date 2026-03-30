import queue
import threading

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

        file_id, chat_id = task

        try:
            send_message(chat_id, "📥 تم استلام الملف...")

            file_path = download_file(file_id)

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


def add_task(file_id, chat_id):
    task_queue.put((file_id, chat_id))


def get_position():
    return task_queue.qsize()