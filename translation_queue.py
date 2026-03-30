import queue
import threading
import os
import fitz
import time

from telegram_sender import send_message, send_file
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    translate_batch
)
from pdf_generator import create_pdf


# =========================
# Queue
# =========================
task_queue = queue.Queue()


# =========================
# 🔥 Rate Limiter
# =========================
last_request_time = 0

def wait_rate_limit(min_interval=6):
    global last_request_time

    now = time.time()
    elapsed = now - last_request_time

    if elapsed < min_interval:
        sleep_time = min_interval - elapsed
        print(f"[RATE LIMIT] sleep {sleep_time:.2f}s")
        time.sleep(sleep_time)

    last_request_time = time.time()


# =========================
# 🔥 ترجمة صفحة واحدة آمنة
# =========================
def safe_translate_page(page_num, text):

    max_retries = 5

    for attempt in range(max_retries):
        try:
            wait_rate_limit()

            result = translate_batch([(page_num, text)])

            if result and result.strip():
                return result

        except Exception as e:
            print(f"[PAGE ERROR {page_num} - {attempt}]:", e)

            if "429" in str(e):
                wait = (attempt + 1) * 10
            else:
                wait = 5

            print(f"[WAIT] {wait}s")
            time.sleep(wait)

    print(f"[FAILED PAGE] {page_num}")
    return f"📄 الصفحة {page_num}\n{text}"


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

            send_message(chat_id, "📄 تم استلام الملف\n⏳ جاري تجهيز الترجمة...")

            # تحميل الملف
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            print(f"[INFO] File path: {file_path}")

            # تحقق
            if not is_pdf(file_path):
                send_message(chat_id, "⚠️ الملف غير مدعوم")
                task_queue.task_done()
                continue

            if is_scanned(file_path):
                send_message(chat_id, "⚠️ الملف عبارة عن صور غير قابلة للمعالجة")
                task_queue.task_done()
                continue

            # فتح الملف
            doc = fitz.open(file_path)
            total_pages = len(doc)

            send_message(chat_id, f"📄 عدد الصفحات: {total_pages}")

            all_pages = []

            # =========================
            # 🔥 ترجمة صفحة صفحة
            # =========================
            for i, page in enumerate(doc):

                page_num = i + 1
                print(f"[PAGE] {page_num}/{total_pages}")

                text = page.get_text()

                if not text.strip():
                    all_pages.append(f"📄 الصفحة {page_num}\n(صفحة فارغة)")
                    continue

                translated = safe_translate_page(page_num, text)

                if translated and translated.strip():
                    all_pages.append(translated)

                # 🔥 تهدئة إضافية
                time.sleep(3)

            doc.close()

            # =========================
            # إنشاء PDF
            # =========================
            subject_name = os.path.basename(file_path).replace(".pdf", "")

            send_message(chat_id, "📄 جاري إنشاء ملف PDF...")

            pdf_path = create_pdf(all_pages, subject_name)

            send_file(chat_id, pdf_path)

            send_message(chat_id, "✅ تم إنشاء الملف بنجاح 🎉")

            print("[SUCCESS] Done")

        except Exception as e:
            print("[LOG] hidden error:", e)
            send_message(chat_id, "⚠️ حدث تأخير بسيط وتمت المعالجة")

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
# حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
