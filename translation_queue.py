import threading
import queue
import os
import fitz
import re
import time

from telegram_sender import send_message
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    clean_text,
    split_pages_into_batches,
    translate_batch
)
from ai_service import call_ai


# =========================
# Queue
# =========================
task_queue = queue.Queue()


# =========================
# تقسيم الرسائل (Telegram limit)
# =========================
def split_message(text, max_len=3500):
def split_message(text, max_len=3800):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


# =========================
# ترجمة صفحة واحدة (Fallback)
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

    for _ in range(3):
        try:
            result = call_ai(messages)
            if result and result.strip():
                return result
        except Exception as e:
            print("Retry page...", e)
            time.sleep(2)

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
                f"📄 عدد الصفحات: {total_pages}\n⏳ جاري الترجمة..."
            )

            # =========================
            # تقسيم إلى batches
            # =========================
            batches = split_pages_into_batches(doc, 4)

            # =========================
            # ترجمة كل batch
            # =========================
            for batch_index, batch in enumerate(batches):

                print(f"[BATCH] {batch_index+1}/{len(batches)}")

                try:
                    translated = translate_batch(batch)
                except Exception as e:
                    print("[BATCH ERROR]", e)
                    translated = None

                # fallback إذا فشل الباتش
                if not translated:
                    print("[FALLBACK] using page-by-page")

                    for page_num, text in batch:
                        translated_page = translate_page(text)

                        msg = f"📄 الصفحة {page_num}\n\n{translated_page}"

                        if len(msg) > 3500:
                        if len(msg) > 3800:
                            for part in split_message(msg):
                                send_message(chat_id, part)
                        else:
                            send_message(chat_id, msg)

                        time.sleep(1)

                    continue

                # =========================
                # إرسال الباتش
                # إرسال كل صفحة لحالها (بدون تكرار)
                # =========================
                if len(translated) > 3500:
                    for part in split_message(translated):
                        send_message(chat_id, part)
                else:
                    send_message(chat_id, translated)
                pages = translated.split("📄 الصفحة")

                time.sleep(2)  # منع 429
                for p in pages:
                    p = p.strip()
                    if not p:
                        continue

                    msg = "📄 الصفحة " + p

                    if len(msg) > 3800:
                        for part in split_message(msg):
                            send_message(chat_id, part)
                    else:
                        send_message(chat_id, msg)

                    time.sleep(1)

            doc.close()

            send_message(chat_id, "✅ تمت ترجمة الملف بالكامل 🎉")
            print("[SUCCESS] Done")

        except Exception as e:
            print("[CRASH]:", e)
            send_message(chat_id, "⚠️ حدث خطأ بسيط، جاري المعالجة...")

        task_queue.task_done()
        print("[END TASK]")


# =========================
# إضافة مهمة
# إضافة مهمة + رقم الطابور
# =========================
def add_task(file_input, chat_id):
    position = task_queue.qsize() + 1
    send_message(chat_id, f"📥 تم إضافة طلبك\n📊 موقعك في الطابور: {position}")
    task_queue.put((file_input, chat_id))


# =========================
# معرفة حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()


# =========================
# تشغيل Worker (Thread)
# =========================
def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()
