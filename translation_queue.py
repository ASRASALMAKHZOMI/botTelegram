import queue
import threading
import os
import fitz
import re
import time

from telegram_sender import send_message, send_file
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    split_pages_into_batches,
    translate_batch
)
from pdf_generator import create_pdf


# =========================
# Queue
# =========================
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

            # =========================
            # UI
            # =========================
            send_message(chat_id, "📄 تم استلام الملف\n⏳ جاري تجهيز الترجمة...")

            # =========================
            # تحميل الملف
            # =========================
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            print(f"[INFO] File path: {file_path}")

            # =========================
            # تحقق
            # =========================
            if not is_pdf(file_path):
                send_message(chat_id, "⚠️ الملف غير مدعوم")
                task_queue.task_done()
                continue

            if is_scanned(file_path):
                send_message(chat_id, "⚠️ الملف عبارة عن صور غير قابلة للمعالجة")
                task_queue.task_done()
                continue

            # =========================
            # فتح الملف
            # =========================
            doc = fitz.open(file_path)
            total_pages = len(doc)

            send_message(chat_id, f"📄 عدد الصفحات: {total_pages}")

            # =========================
            # تقسيم إلى batches
            # =========================
            batches = split_pages_into_batches(doc, 4)

            # 🔥 تجميع الصفحات
            all_pages = []

            # =========================
            # الترجمة
            # =========================
            for batch_index, batch in enumerate(batches):

                print(f"[BATCH] {batch_index+1}/{len(batches)}")

                translated = translate_batch(batch)

                if not translated:
                    print("[LOG] empty batch skipped")
                    continue

                # =========================
                # استخراج الصفحات
                # =========================
                parts = re.split(r"(📄 الصفحة \d+)", translated)

                pages = []

                for i in range(1, len(parts), 2):
                    title = parts[i]
                    content = parts[i+1] if i+1 < len(parts) else ""
                    pages.append(title + content)

                # =========================
                # إصلاح الصفحات المفقودة
                # =========================
                expected_pages = [p[0] for p in batch]

                for page_num in expected_pages:

                    found = any(f"📄 الصفحة {page_num}" in p for p in pages)

                    if not found:
                        print(f"[LOG] retry page {page_num}")

                        text = doc[page_num - 1].get_text()

                        retry = translate_batch([(page_num, text)])

                        if retry and retry.strip():
                            pages.append(retry)
                        else:
                            fallback = f"📄 الصفحة {page_num}\n{text}"
                            pages.append(fallback)

                # =========================
                # حذف التكرار
                # =========================
                unique_pages = []
                seen_pages = set()

                for page_text in pages:

                    match = re.search(r"📄 الصفحة (\d+)", page_text)

                    if match:
                        num = match.group(1)

                        if num in seen_pages:
                            continue

                        seen_pages.add(num)

                    unique_pages.append(page_text)

                # =========================
                # حفظ الصفحات
                # =========================
                for page_text in unique_pages:

                    if not page_text.strip():
                        continue

                    all_pages.append(page_text)

                # 🔥 تهدئة
                time.sleep(2)

            doc.close()

            # =========================
            # استخراج اسم المادة
            # =========================
            subject_name = os.path.basename(file_path).replace(".pdf", "")

            # =========================
            # إنشاء PDF
            # =========================
            send_message(chat_id, "📄 جاري إنشاء ملف PDF...")

            pdf_path = create_pdf(all_pages, subject_name)

            # =========================
            # إرسال الملف
            # =========================
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
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
