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
                print("[ERROR] Not a PDF")
                send_message(chat_id, "❌ فقط PDF مدعوم")
                continue

            if is_scanned(file_path):
                print("[ERROR] Scanned PDF detected")
                send_message(chat_id, "❌ الملف ممسوح (صور) غير مدعوم")
                continue

            # =========================
            # بدء الترجمة
            # =========================
            print("[STEP] Starting translation...")
            send_message(chat_id, "⏳ جاري الترجمة...")

            output = translate_pdf(file_path)

            print(f"[STEP] Translation finished. Output: {output}")

            # =========================
            # التحقق من وجود الملف
            # =========================
            if not os.path.exists(output):
                print("[ERROR] Output file not found!")
                send_message(chat_id, "❌ فشل إنشاء الملف المترجم")
                continue

            # =========================
            # إرسال الملف
            # =========================
            print("[STEP] Sending file to user...")
            send_message(chat_id, "📤 جاري إرسال الملف...")

            send_file(chat_id, output)

            print("[SUCCESS] File sent successfully ✅")

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

    # حساب الترتيب
    position = task_queue.qsize() + 1

    print(f"[QUEUE] New task added. Position: {position}")

    task_queue.put((file_input, chat_id))

    send_message(chat_id, f"📌 تم إضافتك للطابور\n🔢 ترتيبك: {position}")


# =========================
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
