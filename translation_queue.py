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
waiting_users = []


# =========================
# Helpers
# =========================
def progress_bar(p):
    bars = int(p / 10)
    return "█" * bars + "░" * (10 - bars)


def format_time(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}m {seconds}s"


# =========================
# ETA Predictive 
# =========================
def estimate_eta(full_text):
    total_chars = len(full_text)

    tokens = total_chars / 4  # تقريب

    wait_blocks = int(tokens // 7000)
    wait_time = wait_blocks * 60

    processing_time = tokens * 0.005

    return int(wait_time + processing_time)


# =========================
# Countdown Thread (تنازلي فقط)
# =========================
def countdown_updater(state, chat_id, msg_id, position):

    last_time = time.time()

    while not state["done"]:

        now = time.time()
        diff = now - last_time
        last_time = now

        if state["remaining"] > 0:
            state["remaining"] -= diff

        eta = format_time(state["remaining"])
        bar = progress_bar(state["progress"])

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
    while True:

        task = task_queue.get()
        if task is None:
            break

        file_input, chat_id, msg_id = task

        try:
            # =========================
            # تحميل الملف
            # =========================
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            if not is_pdf(file_path):
                edit_message(chat_id, msg_id, "❌ فقط PDF")
                continue

            if is_scanned(file_path):
                edit_message(chat_id, msg_id, "❌ الملف صور")
                continue

            doc = fitz.open(file_path)

            # =========================
            # جمع النص كامل (🔥 مهم)
            # =========================
            full_text = ""

            for page in doc:
                full_text += page.get_text()

            # =========================
            # حساب ETA مرة واحدة فقط
            # =========================
            eta = estimate_eta(full_text)

            state = {
                "remaining": eta,
                "progress": 0,
                "done": False
            }

            # =========================
            # تشغيل العداد
            # =========================
            timer_thread = threading.Thread(
                target=countdown_updater,
                args=(state, chat_id, msg_id, 1),
                daemon=True
            )
            timer_thread.start()

            translated_pages = []
            total_pages = len(doc)

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

                # تحديث البروقراس فقط
                progress = int((page_num / total_pages) * 100)
                state["progress"] = progress

            doc.close()

            state["done"] = True

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

            send_file(chat_id, pdf_path)

            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        except Exception as e:
            print("ERROR:", e)
            send_message(chat_id, "⚠️ خطأ أثناء الترجمة")

        finally:
            task_queue.task_done()

            # تحديث الطابور 🔥
            if waiting_users:
                waiting_users.pop(0)

            for i, (chat_id_w, msg_id_w) in enumerate(waiting_users):
                try:
                    edit_message(
                        chat_id_w,
                        msg_id_w,
                        f"""⏳ رقمك في الطابور: {i+1}

🚀 سيتم بدء الترجمة قريبًا..."""
                    )
                except:
                    pass


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):

    position = task_queue.qsize() + 1

    msg_id = send_message(
        chat_id,
        f"""⏳ رقمك في الطابور: {position}

🚀 في الانتظار..."""
    )

    waiting_users.append((chat_id, msg_id))

    task_queue.put((file_input, chat_id, msg_id))


# =========================
# تشغيل
# =========================
def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()
