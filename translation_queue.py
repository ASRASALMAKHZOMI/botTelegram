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
    translate_batch,
    translate_page
)
from ai_service import call_ai


# =========================
# Queue
# =========================
task_queue = queue.Queue()


# =========================
# تقسيم الرسائل (Telegram limit)
# =========================
def split_message(text, max_len=3800):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


# =========================
# التحقق هل الصفحة مترجمة فعلاً
# =========================
def is_translated(text):
    # إذا فيه عربي → غالباً مترجم
    return bool(re.search(r'[\u0600-\u06FF]', text))


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
                send_message(chat_id, "❌ الملف عبارة عن صور (غير مدعوم حالياً)")
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

                # =========================
                # fallback ذكي (إذا فشل الباتش)
                # =========================
                if not translated:
                    print("[FALLBACK] page-by-page")

                    for page_num, text in batch:
                        translated_page = translate_page(text)

                        msg = f"📄 الصفحة {page_num}\n\n{translated_page}"

                        if len(msg) > 3800:
                            for part in split_message(msg):
                                send_message(chat_id, part)
                        else:
                            send_message(chat_id, msg)

                        time.sleep(2)

                    continue

                # =========================
                # تقسيم الصفحات بشكل قوي
                # =========================
                parts = re.split(r"(📄 الصفحة\s*\d+)", translated)

                pages_dict = {}

                current_page = None

                for part in parts:
                    part = part.strip()
                    if not part:
                        continue

                    if "📄 الصفحة" in part:
                        current_page = part
                        pages_dict[current_page] = ""
                    else:
                        if current_page:
                            pages_dict[current_page] += part + "\n"

                # =========================
                # إرسال كل صفحة + تحقق الترجمة
                # =========================
                for key, content in pages_dict.items():

                    content = content.strip()

                    # 🔥 تنظيف خفيف بدون تخريب
                    lines = content.split("\n")
                    cleaned_lines = []

                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line:
                            continue

                        # حذف التكرار فقط لو متكرر مباشرة
                        if i > 0 and line == lines[i-1]:
                            continue

                        cleaned_lines.append(line)

                    content = "\n".join(cleaned_lines)

                    # 🔥 تحقق إذا الصفحة ما ترجمت
                    if not is_translated(content):
                        print("[RETRY PAGE]", key)

                        page_num = int(re.findall(r'\d+', key)[0])
                        original_text = next(t for p, t in batch if p == page_num)

                        content = translate_page(original_text)

                    msg = f"{key}\n\n{content}"

                    if len(msg) > 3800:
                        for part in split_message(msg):
                            send_message(chat_id, part)
                    else:
                        send_message(chat_id, msg)

                    time.sleep(2)

                # تقليل الضغط (مهم)
                time.sleep(5)

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
# =========================
def add_task(file_input, chat_id):
    position = task_queue.qsize() + 1
    send_message(chat_id, f"📥 تم إضافة طلبك\n📊 موقعك في الطابور: {position}")
    task_queue.put((file_input, chat_id))


# =========================
# معرفة الطابور
# =========================
def get_position():
    return task_queue.qsize()


# =========================
# تشغيل Worker
# =========================
def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()
