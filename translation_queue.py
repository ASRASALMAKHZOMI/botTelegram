import queue
import threading
import os
import fitz

from telegram_sender import send_message
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    split_pages_into_batches,
    translate_batch
)

task_queue = queue.Queue()


# =========================
# تقسيم الرسائل (Telegram limit)
# =========================
def split_message(text, max_len=3500):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


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

            send_message(chat_id, "🚀 جاري بدء الترجمة...")

            # =========================
            # تحديد الملف
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
                send_message(chat_id, "❌ الملف عبارة عن صور (غير مدعوم)")
                continue

            # =========================
            # فتح الملف
            # =========================
            doc = fitz.open(file_path)
            total_pages = len(doc)

            send_message(
                chat_id,
                f"📄 عدد الصفحات: {total_pages}\n⏳ جاري الترجمة..."
            )

            # =========================
            # تقسيم إلى batches (كل 10 صفحات)
            # =========================
            batches = split_pages_into_batches(doc, 10)

            # =========================
            # ترجمة كل batch
            # =========================
            for batch_index, batch in enumerate(batches):

                print(f"[BATCH] {batch_index+1}/{len(batches)}")

                translated = translate_batch(batch)

                # =========================
                # تقسيم الناتج حسب الصفحات
                # =========================
                pages_output = translated.split("📄 الصفحة")

                for page_text in pages_output:

                    if not page_text.strip():
                        continue

                    page_text = "📄 الصفحة " + page_text.strip()

                    # =========================
                    # إرسال الصفحة
                    # =========================
                    if len(page_text) > 3500:
                        parts = split_message(page_text)
                        for part in parts:
                            send_message(chat_id, part)
                    else:
                        send_message(chat_id, page_text)

            doc.close()

            # =========================
            # نهاية الترجمة
            # =========================
            send_message(chat_id, "✅ تم الانتهاء من الترجمة بنجاح")

            print("[SUCCESS] All pages sent ✅")

        except Exception as e:
            print("[CRASH] Translation Error:", e)
            send_message(chat_id, "❌ حدث خطأ أثناء الترجمة")

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
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
