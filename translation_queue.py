import threading
import queue
import os
import fitz

from telegram_sender import send_message, edit_message, delete_message, send_file
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    translate_page_json,
    format_page_from_json
)
from pdf_generator import create_pdf


# =========================
# Queue
# =========================
task_queue = queue.Queue()


# =========================
# Progress Bar 🔥
# =========================
def progress_bar(p):
    bars = int(p / 10)
    return "█" * bars + "░" * (10 - bars)


# =========================
# Worker
# =========================
def worker():
    while True:

        task = task_queue.get()

        if task is None:
            break

        file_input, chat_id = task
        translated_pages = []

        try:
            print("\n======================")
            print(f"[START] Task for chat_id: {chat_id}")

            # =========================
            # رسالة البداية
            # =========================
            position = task_queue.qsize()

            msg_id = send_message(
                chat_id,
                f"⏳ رقمك في الطابور: {position}\n\n🚀 جاري الترجمة...\n\n[░░░░░░░░░░] 0%"
            )

            # =========================
            # تحديد الملف
            # =========================
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            # =========================
            # تحقق
            # =========================
            if not is_pdf(file_path):
                edit_message(chat_id, msg_id, "❌ فقط ملفات PDF مدعومة")
                continue

            if is_scanned(file_path):
                edit_message(chat_id, msg_id, "❌ الملف عبارة عن صور (غير مدعوم)")
                continue

            # =========================
            # فتح الملف
            # =========================
            doc = fitz.open(file_path)
            total_pages = len(doc)

            last_progress = -1

            # =========================
            # الترجمة
            # =========================
            for page_num, page in enumerate(doc, start=1):

                text = page.get_text().strip()

                if not text:
                    continue

                page_json = translate_page_json(text, page_num)

                if not page_json:
                    continue

                translated = format_page_from_json(page_json)

                translated_pages.append(
                    f"📄 الصفحة {page_num}\n\n{translated}"
                )

                # =========================
                # تحديث التقدم
                # =========================
                progress = int((page_num / total_pages) * 100)

                if progress != last_progress and progress % 5 == 0:
                    bar = progress_bar(progress)

                    try:
                        edit_message(
                            chat_id,
                            msg_id,
                            f"⏳ رقمك في الطابور: {position}\n\n🚀 جاري الترجمة...\n\n[{bar}] {progress}%"
                        )
                    except:
                        pass

                    last_progress = progress

            doc.close()

            # =========================
            # حذف رسالة التقدم
            # =========================
            try:
                delete_message(chat_id, msg_id)
            except:
                pass

            # =========================
            # إنشاء PDF
            # =========================
            pdf_path = create_pdf(
                translated_pages,
                subject_name="Translation File",
                output_path=f"translated_{chat_id}.pdf"
            )

            # =========================
            # إرسال الملف
            # =========================
            send_file(chat_id, pdf_path)

            # تنظيف الملف
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            print("[SUCCESS] Done")

        except Exception as e:
            print("[CRASH]:", e)
            send_message(chat_id, "⚠️ حدث خطأ أثناء الترجمة")

        finally:
            task_queue.task_done()
            print("[END TASK]")


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):
    task_queue.put((file_input, chat_id))


# =========================
# ترتيب الطابور
# =========================
def get_position():
    return task_queue.qsize()


# =========================
# تشغيل Workers
# =========================
def start_worker(num_workers=2):
    for _ in range(num_workers):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
