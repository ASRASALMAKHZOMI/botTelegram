import threading
import queue
import os
import fitz
import time

from telegram_sender import send_message
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    translate_page_json,
    format_page_from_json,
    save_page_json
)

# =========================
# Queue
# =========================
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

            send_message(chat_id, "🚀 بدء الترجمة...")
            send_message(chat_id, "📄 تم استلام الملف\n⏳ جاري تجهيز الترجمة...")

            # =========================
            # تحديد الملف
            # =========================
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            # =========================
            # التحقق
            # =========================
            if not is_pdf(file_path):
                send_message(chat_id, "❌ فقط ملفات PDF مدعومة")
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
                f"📄 عدد الصفحات: {total_pages}\n⏳ جاري الترجمة صفحة صفحة..."
            )

            # =========================
            # ترجمة صفحة صفحة 🔥
            # =========================
            for page_num, page in enumerate(doc, start=1):

                print(f"[PAGE] {page_num}/{total_pages}")

                text = page.get_text().strip()

                if not text:
                    continue

                # ⏳ تهدئة بسيطة
                time.sleep(2)

                # =========================
                # ترجمة → JSON فقط
                # =========================
                page_json = translate_page_json(text, page_num)

                if not page_json:
                    print(f"[ERROR] Failed page {page_num}")
                    send_message(chat_id, f"❌ فشل ترجمة الصفحة {page_num}")
                    continue

                # =========================
                # حفظ JSON
                # =========================
                save_page_json(page_json)

                # =========================
                # تنسيق (من الكود فقط)
                # =========================
                translated = format_page_from_json(page_json)

                # =========================
                # إرسال
                # =========================
                msg = f"📄 الصفحة {page_num}\n\n{translated}"

                if len(msg) > 3500:
                    for part in split_message(msg):
                        send_message(chat_id, part)
                        time.sleep(1.2)
                else:
                    send_message(chat_id, msg)
                    time.sleep(1.2)

            doc.close()

            send_message(chat_id, "✅ تمت ترجمة الملف بالكامل 🎉")
            print("[SUCCESS] Done")

        except Exception as e:
            print("[CRASH]:", e)
            send_message(chat_id, "⚠️ حدث خطأ أثناء الترجمة")

        task_queue.task_done()
        print("[END TASK]")


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):
    task_queue.put((file_input, chat_id))


# =========================
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()


# =========================
# تشغيل Worker
# =========================
def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()
