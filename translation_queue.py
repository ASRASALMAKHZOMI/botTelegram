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
# Queue + State
# =========================
task_queue = queue.Queue()
waiting_users = []
queue_lock = threading.Lock()


# =========================
# Helpers
# =========================
def progress_bar(p):
    bars = int(p / 10)
    return "█" * bars + "░" * (10 - bars)


def update_ui(chat_id, msg_id, position, stage, progress):
    bar = progress_bar(progress)

    try:
        edit_message(
            chat_id,
            msg_id,
            f"""⏳ رقمك في الطابور: {position}

{stage}

[{bar}] {progress}%"""
        )
    except:
        pass


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
            # تحديد موقعه الحالي
            # =========================
            with queue_lock:
                for i, user in enumerate(waiting_users):
                    if user["chat_id"] == chat_id:
                        position = i + 1
                        break
                else:
                    position = 1

            # =========================
            # 1. تحميل
            # =========================
            update_ui(chat_id, msg_id, position, "📥 جاري تحميل الملف...", 5)

            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            update_ui(chat_id, msg_id, position, "📥 تم تحميل الملف", 10)

            # =========================
            # 2. استخراج النص
            # =========================
            update_ui(chat_id, msg_id, position, "📄 جاري استخراج النص...", 15)

            if not is_pdf(file_path):
                edit_message(chat_id, msg_id, "❌ فقط PDF")
                continue

            if is_scanned(file_path):
                edit_message(chat_id, msg_id, "❌ الملف صور")
                continue

            doc = fitz.open(file_path)

            full_text = ""
            for page in doc:
                full_text += page.get_text()

            update_ui(chat_id, msg_id, position, "📄 تم استخراج النص", 20)

            # =========================
            # 3. معالجة
            # =========================
            update_ui(chat_id, msg_id, position, "🔎 جاري معالجة النص...", 25)
            time.sleep(0.5)
            update_ui(chat_id, msg_id, position, "🔎 جاهز للترجمة", 30)

            # =========================
            # 4. الترجمة
            # =========================
            translated_pages = []
            total_pages = len(doc)

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

                progress = 30 + int((page_num / total_pages) * 50)

                update_ui(chat_id, msg_id, position, "🌐 جاري الترجمة...", progress)

            doc.close()

            # =========================
            # 5. إنشاء PDF
            # =========================
            update_ui(chat_id, msg_id, position, "🧾 جاري إنشاء PDF...", 85)

            pdf_path = create_pdf(
                translated_pages,
                subject_name="Translation File",
                output_path=f"translated_{chat_id}.pdf"
            )

            update_ui(chat_id, msg_id, position, "🧾 تم إنشاء الملف", 95)

            # =========================
            # 6. إرسال
            # =========================
            update_ui(chat_id, msg_id, position, "📤 جاري الإرسال...", 98)

            send_file(chat_id, pdf_path)
            # 🔥 إرجاع الأزرار
            keyboard = [
            ["📚 الملازم", "📊 الجداول"],
            ["💻 تحدي البرمجة", "🧠 مساعد الدراسة الذكي"],
            ["🌍 ترجمة المستندات"],
            ["👤 من نحن"]
            ]

            send_message(chat_id, "اختر ما تحتاج:", keyboard)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            update_ui(chat_id, msg_id, position, "✅ تم الإرسال", 100)

            time.sleep(1)
            delete_message(chat_id, msg_id)

        except Exception as e:
            print("ERROR:", e)
            send_message(chat_id, "⚠️ حدث خطأ أثناء الترجمة")

        finally:
            task_queue.task_done()

            # =========================
            # تحديث الطابور (🔥 أهم جزء)
            # =========================
            with queue_lock:

                if waiting_users:
                    waiting_users.pop(0)

                for i, user in enumerate(waiting_users):
                    new_pos = i + 1

                    try:
                        edit_message(
                            user["chat_id"],
                            user["msg_id"],
                            f"""⏳ رقمك في الطابور: {new_pos}

🚀 في الانتظار..."""
                        )
                    except:
                        pass


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):

    with queue_lock:
        position = len(waiting_users) + 1

        msg_id = send_message(
            chat_id,
            f"""⏳ رقمك في الطابور: {position}

🚀 في الانتظار..."""
        )

        waiting_users.append({
            "chat_id": chat_id,
            "msg_id": msg_id
        })

    task_queue.put((file_input, chat_id, msg_id))


# =========================
# تشغيل
# =========================
def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()
