import queue
import threading
import os
import fitz
import time

from telegram_sender import send_message, send_file
from translation_system import (
    download_file,
    is_pdf,
    is_scanned,
    translate_batch,
    split_pages_into_batches  # 🔥 استيراد دالة التجميع
)
from pdf_generator import create_pdf


# =========================
# Queue & Lock
# =========================
task_queue = queue.Queue()
api_lock = threading.Lock()  # 🔥 قفل لحماية الـ API من تداخل الثريدات


# =========================
# 🔥 Rate Limiter محسن
# =========================
last_request_time = 0

def wait_rate_limit(min_interval=15):  # 🔥 الوقت ثابت لحماية الـ API
    global last_request_time
    
    with api_lock:  # 🔥 حماية المتغير العام بقفل
        now = time.time()
        elapsed = now - last_request_time

        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            print(f"[RATE LIMIT] sleep {sleep_time:.2f}s")
            time.sleep(sleep_time)

        last_request_time = time.time()


# =========================
# 🔥 ترجمة Batch آمنة
# =========================
def safe_translate_batch(pages_batch):
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            wait_rate_limit()  # انتظار قبل كل طلب
            
            result = translate_batch(pages_batch)
            
            if result and result.strip():
                return result
                
        except Exception as e:
            print(f"[BATCH ERROR {attempt + 1}/{max_retries}]:", e)
            
            if "429" in str(e):
                wait = 20  # انتظار طويل جداً في حالة 429
            else:
                wait = 5
            
            print(f"[WAIT] {wait}s")
            time.sleep(wait)
    
    # 🔥 Fallback: إرجاع النص الأصلي في حال الفشل النهائي
    print("[FALLBACK] using original text for batch")
    fallback = ""
    for page_num, text in pages_batch:
        fallback += f"📄 الصفحة {page_num}\n{text}\n"
    return fallback


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

            send_message(chat_id, "📄 تم استلام الملف\n⏳ جاري تجهيز الترجمة...")

            # تحميل الملف
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)

            print(f"[INFO] File path: {file_path}")

            # تحقق
            if not is_pdf(file_path):
                send_message(chat_id, "⚠️ الملف غير مدعوم")
                task_queue.task_done()
                continue

            if is_scanned(file_path):
                send_message(chat_id, "⚠️ الملف عبارة عن صور غير قابلة للمعالجة")
                task_queue.task_done()
                continue

            # فتح الملف
            doc = fitz.open(file_path)
            total_pages = len(doc)

            send_message(chat_id, f"📄 عدد الصفحات: {total_pages}")

            all_pages = []

            # =========================
            # 🔥 استخدام التجميع (Batching) - 🔥 التعديل هنا (2 بدلاً من 4)
            # =========================
            batches = split_pages_into_batches(doc, batch_size=2)  # 🔥 تم التعديل إلى 2
            total_batches = len(batches)
            
            print(f"[INFO] Total batches: {total_batches}")

            for i, batch in enumerate(batches):
                print(f"[BATCH] {i + 1}/{total_batches}")
                
                # ترجمة المجموعة
                translated_batch_text = safe_translate_batch(batch)
                
                if translated_batch_text:
                    all_pages.append(translated_batch_text)
                
                # 🔥 تهدئة إضافية بين الباتشات
                time.sleep(2)

            doc.close()

            # =========================
            # إنشاء PDF
            # =========================
            subject_name = os.path.basename(file_path).replace(".pdf", "")

            send_message(chat_id, "📄 جاري إنشاء ملف PDF...")

            pdf_path = create_pdf(all_pages, subject_name)

            send_file(chat_id, pdf_path)

            send_message(chat_id, "✅ تم إنشاء الملف بنجاح 🎉")

            print("[SUCCESS] Done")

        except Exception as e:
            print("[LOG] hidden error:", e)
            send_message(chat_id, "⚠️ حدث خطأ أثناء المعالجة، يرجى المحاولة لاحقاً")

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
# حجم الطابور
# =========================
def get_position():
    return task_queue.qsize()
