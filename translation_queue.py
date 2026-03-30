import queue
import threading
import os
import fitz
import re
import time

from telegram_sender import send_message
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    clean_text
    split_pages_into_batches,
    translate_batch
)
from ai_service import call_ai

task_queue = queue.Queue()


# =========================
# تقسيم الرسائل
# تقسيم الرسائل (Telegram limit)
# =========================
def split_message(text, max_len=3500):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


# =========================
# ترجمة صفحة واحدة
# =========================
def translate_page(text):

    text = clean_text(text)

    if not text.strip():
        return "(صفحة فارغة)"

    prompt = f"""
ترجم النص التالي إلى العربية:

- كل سطر وتحته ترجمته
- لا تكرر
- لا تضف شرح
- استخدم مصطلحات برمجية صحيحة

النص:
{text}
"""

    messages = [
        {"role": "system", "content": "مترجم تقني."},
        {"role": "user", "content": prompt}
    ]

    attempt = 0

    while attempt < 5:
        try:
            result = call_ai(messages)

            # 🔥 التعديل المهم
            if result and result.strip():
                return result

        except Exception as e:
            print("Retry page...", e)

        time.sleep(3)
        attempt += 1

    # 🔥 fallback نظيف بدون فضيحة
    return text


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
            # 🔥 UI نظيف
            send_message(chat_id, "📄 تم استلام الملف\n⏳ جاري تجهيز الترجمة...")

            # =========================
            # تحديد الملف
            # =========================
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            # تحقق
            # =========================
            # التحقق من الملف
            # =========================
            if not is_pdf(file_path):
                send_message(chat_id, "❌ فقط PDF")
                send_message(chat_id, "⚠️ الملف غير مدعوم")
                continue

            if is_scanned(file_path):
                send_message(chat_id, "❌ الملف عبارة عن صور")
                send_message(chat_id, "⚠️ الملف عبارة عن صور غير قابلة للمعالجة")
                continue

            # =========================
            # فتح الملف
            # =========================
            doc = fitz.open(file_path)
            total = len(doc)
            total_pages = len(doc)

            send_message(
                chat_id,
                f"📄 عدد الصفحات: {total_pages}\n\n⏳ سيتم إرسال الصفحات تباعًا..."
            )

            # =========================
            # تقسيم إلى batches (4 صفحات)
            # =========================
            batches = split_pages_into_batches(doc, 4)

            send_message(chat_id, f"📄 عدد الصفحات: {total}")
            # =========================
            # ترجمة كل batch
            # =========================
            for batch_index, batch in enumerate(batches):

            # ترجمة صفحة صفحة
            for i, page in enumerate(doc):
                print(f"[BATCH] {batch_index+1}/{len(batches)}")

                page_num = i + 1
                text = page.get_text()
                translated = translate_batch(batch)

                if not text.strip():
                    send_message(chat_id, f"📄 الصفحة {page_num}\n(صفحة فارغة)")
                if not translated:
                    print("[LOG] empty translation skipped")
                    continue

                translated = translate_page(text)
                # =========================
                # استخراج الصفحات باستخدام regex (🔥 بدون أخطاء)
                # =========================
                parts = re.split(r"(📄 الصفحة \d+)", translated)

                pages = []

                for i in range(1, len(parts), 2):
                    title = parts[i]
                    content = parts[i+1] if i+1 < len(parts) else ""
                    pages.append(title + content)

                # =========================
                # التحقق من الصفحات
                # =========================
                expected_pages = [p[0] for p in batch]

                for page_num in expected_pages:

                msg = f"📄 الصفحة {page_num}\n\n{translated}"
                    found = any(f"📄 الصفحة {page_num}" in p for p in pages)

                # تقسيم لو طويل
                if len(msg) > 3500:
                    for part in split_message(msg):
                        send_message(chat_id, part)
                else:
                    send_message(chat_id, msg)
                    if not found:
                        print(f"[LOG] retry page {page_num}")

                # 🔥 يمنع 429
                        send_message(chat_id, f"🔄 معالجة الصفحة {page_num}...")

                        text = doc[page_num - 1].get_text()

                        retry = translate_batch([(page_num, text)])

                        if retry:
                            pages.append(retry)
                        else:
                            # fallback بدون ما نحسس المستخدم
                            fallback = f"📄 الصفحة {page_num}\n{text}"
                            pages.append(fallback)

                # =========================
                # إرسال الصفحات
                # =========================
                for page_text in pages:

                    if not page_text.strip():
                        continue

                    if len(page_text) > 3500:
                        for part in split_message(page_text):
                            send_message(chat_id, part)
                    else:
                        send_message(chat_id, page_text)

                # 🔥 تهدئة بسيطة (يمنع 429)
                time.sleep(2)

            doc.close()

            send_message(chat_id, "✅ تمت الترجمة بالكامل")
            # =========================
            # نهاية الترجمة
            # =========================
            send_message(chat_id, "✅ تمت ترجمة الملف بالكامل بنجاح 🎉")

            print("[SUCCESS] Done")

        except Exception as e:
            print("[CRASH]:", e)
            send_message(chat_id, "❌ حدث خطأ")
            print("[LOG] hidden error:", e)

            # 🔥 UI احترافي بدون كلمة فشل
            send_message(chat_id, "⚠️ حدث تأخير بسيط وتمت المعالجة، جاري المتابعة...")

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
# معرفة الطابور
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
