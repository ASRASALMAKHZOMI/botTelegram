import threading
import queue
import os
import fitz
import time

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
# Global Stats
# =========================
avg_task_time = 120
completed_tasks = 0


# =========================
# Progress Bar
# =========================
def progress_bar(p):
    bars = int(p / 10)
    return "█" * bars + "░" * (10 - bars)


def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}m {seconds}s"


# =========================
# Countdown Thread
# =========================
def countdown_updater(state, chat_id, msg_id, position):

    while not state["done"]:

        if state["remaining"] > 0:
            state["remaining"] -= 1

        bar = progress_bar(state["progress"])
        eta = format_time(state["remaining"])

        try:
            edit_message(
                chat_id,
                msg_id,
                f"""⏳ رقمك في الطابور: {position}

🚀 جاري الترجمة...

[{bar}] {state["progress"]}%

⏱ المتبقي: {eta}
"""
            )
        except:
            pass

        time.sleep(2)


# =========================
# Worker
# =========================
def worker():
    global avg_task_time, completed_tasks

    while True:

        task = task_queue.get()
        if task is None:
            break

        file_input, chat_id = task

        try:
            start_time = time.time()

            position = 1

            estimated_wait = (task_queue.qsize()) * avg_task_time

            msg_id = send_message(
                chat_id,
                f"""⏳ رقمك في الطابور: {position}

⏱ وقت الانتظار المتوقع: {format_time(estimated_wait)}

🚀 سيتم بدء الترجمة قريبًا..."""
            )

            # =========================
            # تحميل الملف
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

            doc = fitz.open(file_path)

            # =========================
            # حساب chunks
            # =========================
            total_chunks = sum(
                (len(page.get_text().split("\n")) // 8 + 1)
                for page in doc
            )

            processed_chunks = 0

            state = {
                "remaining": 0,
                "progress": 0,
                "done": False
            }

            # =========================
            # تشغيل العداد
            # =========================
            timer_thread = threading.Thread(
                target=countdown_updater,
                args=(state, chat_id, msg_id, position),
                daemon=True
            )
            timer_thread.start()

            translated_pages = []

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
                # حساب التقدم والوقت
                # =========================
                chunks = len(text.split("\n")) // 8 + 1
                processed_chunks += chunks

                elapsed = time.time() - start_time

                if processed_chunks > 0:
                    avg = elapsed / processed_chunks
                    remaining_chunks = total_chunks - processed_chunks
                    remaining_time = int(avg * remaining_chunks)
                else:
                    remaining_time = 0

                state["remaining"] = remaining_time
                state["progress"] = int((processed_chunks / total_chunks) * 100)

            doc.close()

            state["done"] = True

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

            # تنظيف
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            # =========================
            # تحديث المتوسط
            # =========================
            task_time = time.time() - start_time

            completed_tasks += 1
            avg_task_time = (
                (avg_task_time * (completed_tasks - 1)) + task_time
            ) / completed_tasks

        except Exception as e:
            print("ERROR:", e)
            send_message(chat_id, "⚠️ حدث خطأ أثناء الترجمة")

        finally:
            task_queue.task_done()


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):
    position = task_queue.qsize() + 1
    estimated_wait = (position - 1) * avg_task_time

    send_message(
        chat_id,
        f"""⏳ رقمك في الطابور: {position}

⏱ وقت الانتظار المتوقع: {format_time(estimated_wait)}"""
    )

    task_queue.put((file_input, chat_id))


# =========================
# تشغيل
# =========================
def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()
