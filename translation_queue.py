import queue
import threading
import os

from telegram_sender import send_message
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    translate_to_text
)

task_queue = queue.Queue()


# =========================
# تقسيم الرسائل (limit تيليجرام)
# =========================
def split_message(text, max_len=3500):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


# =========================
# تقسيم حسب الصفحات (كل 3 صفحات)
# =========================
def split_by_pages(text, pages_per_chunk=3):

    chunks = []
    current = []
    count = 0

    lines = text.split("\n")

    for line in lines:

        if line.startswith("📄 الصفحة"):
            count += 1

        current.append(line)

        if count == pages_per_chunk:
            chunks.append("\n".join(current))
            current = []
            count = 0

    if current:
        chunks.append("\n".join(current))

    return chunks


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

            send_message(chat_id, "🚀 جاء دورك الآن، جاري بدء الترجمة...")

            # =========================
            # تحديد نوع الملف
            # =========================
            if os.path.exists(file_input):
                print("[INFO] Using local file path")
                file_path = file_input
            else:
                print("[INFO] Downloading from Telegram...")
                file_path = download_file(file_input)

            print(f"[INFO] File path: {file_path}")

            # =========================
            # التحقق من الملف
            # =========================
            if not is_pdf(file_path):
                send_message(chat_id, "❌ فقط PDF مدعوم")
                continue

            if is_scanned(file_path):
                send_message(chat_id, "❌ الملف ممسوح (صور) غير مدعوم")
                continue

            # =========================
            # بدء الترجمة
            # =========================
            send_message(chat_id, "⏳ جاري الترجمة...")

            translated_text = translate_to_text(file_path)

            # =========================
            # تقسيم حسب الصفحات (كل 3 صفحات)
            # =========================
            page_chunks = split_by_pages(translated_text, 3)

            for chunk in page_chunks:

                # تقسيم إضافي لو الرسالة طويلة
                if len(chunk) > 3500:
                    parts = split_message(chunk)
                    for part in parts:
                        send_message(chat_id, part)
                else:
                    send_message(chat_id, chunk)

            print("[SUCCESS] Sent in page chunks ✅")

        except Exception as e:
            print("[CRASH] Translation Error:", e)
            send_message(chat_id, "❌ حدث خطأ أثناء الترجمة")

        task_queue.task_done()
        print("[END TASK]")
        print("======================\n")


# =========================
# تشغيل Workers
# =========================
def start_workers(n=2):
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
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
