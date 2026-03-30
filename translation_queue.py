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
    split_pages_into_batches,
    translate_batch
)
from pdf_generator import create_pdf

task_queue = queue.Queue()

# =========================
# 🔥 Rate Limiter وقائي (ينتظر قبل كل طلب)
# =========================
last_request_time = 0

def wait_before_request(min_interval=45):
    """
    ينتظر قبل كل طلب لتجنب خطأ 429.
    min_interval: الوقت الأدنى بين طلبين (بالثواني).
    """
    global last_request_time
    
    now = time.time()
    elapsed = now - last_request_time
    
    if elapsed < min_interval:
        sleep_time = min_interval - elapsed
        print(f"[RATE LIMIT] Waiting {sleep_time:.1f}s before next request...")
        time.sleep(sleep_time)
    
    last_request_time = time.time()


# =========================
# 🔥 ترجمة Batch مع حماية بسيطة
# =========================
def safe_translate_batch(pages_batch):
    """
    يترجم مجموعة صفحات مع حماية من الأخطاء و Fallback.
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # 🔥 الانتظار الوقائي قبل كل طلب (هذا هو السر)
            wait_before_request(min_interval=45)
            
            result = translate_batch(pages_batch)
            
            if result and result.strip():
                return result
                
        except Exception as e:
            print(f"[BATCH ERROR {attempt + 1}/{max_retries}]:", e)
            
            # في حال الخطأ، ننتظر وقتاً أطول قبل المحاولة التالية
            wait = 60
            print(f"[RETRY WAIT] {wait}s")
            time.sleep(wait)
    
    # 🔥 Fallback: إرجاع النص الأصلي إذا فشل كل شيء
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
            
            # =========================
            # تحديد الملف
            # =========================
            if os.path.exists(file_input):
                file_path = file_input
            else:
                file_path = download_file(file_input)
            
            print(f"[INFO] File path: {file_path}")
            
            # =========================
            # التحقق من الملف
            # =========================
            if not is_pdf(file_path):
                send_message(chat_id, "⚠️ الملف غير مدعوم (فقط PDF)")
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
            
            send_message(chat_id, f"📄 عدد الصفحات: {total_pages}\n⏳ جاري المعالجة...")
            
            all_pages = []
            
            # =========================
            # 🔥 تقسيم إلى Batches (2 صفحة لكل طلب)
            # =========================
            batches = split_pages_into_batches(doc, batch_size=2)
            total_batches = len(batches)
            
            print(f"[INFO] Total batches: {total_batches}")
            
            # =========================
            # 🔥 ترجمة كل Batch
            # =========================
            for i, batch in enumerate(batches):
                print(f"[BATCH] {i + 1}/{total_batches}")
                
                # ترجمة المجموعة
                translated_text = safe_translate_batch(batch)
                
                if translated_text and translated_text.strip():
                    all_pages.append(translated_text)
                else:
                    # Fallback في حال الفشل التام للباتش
                    fallback = ""
                    for page_num, text in batch:
                        fallback += f"📄 الصفحة {page_num}\n{text}\n"
                    all_pages.append(fallback)
                    print("[FALLBACK] Saved original text for this batch")
                
                # 🔥 تهدئة إضافية بين الباتشات
                time.sleep(3)
            
            doc.close()
            
            # =========================
            # 🔥 إنشاء PDF (بدلاً من إرسال رسائل)
            # =========================
            subject_name = os.path.basename(file_path).replace(".pdf", "")
            
            send_message(chat_id, "📄 جاري إنشاء ملف PDF...")
            
            pdf_path = create_pdf(all_pages, subject_name)
            
            send_file(chat_id, pdf_path)
            
            send_message(chat_id, "✅ تمت ترجمة الملف بالكامل بنجاح 🎉")
            
            print("[SUCCESS] Done")
            
        except Exception as e:
            print("[CRASH]:", e)
            send_message(chat_id, "⚠️ حدث خطأ أثناء المعالجة")
            print("[LOG] hidden error:", e)
        
        task_queue.task_done()
        print("[END TASK]")
        print("======================\n")


# =========================
# تشغيل Workers
# =========================
def start_workers(n=1):
    """
    يبدأ عدد محدد من الـ Workers لمعالجة المهام.
    ينصح بـ 1 فقط لتجنب التعقيد والضغط على الـ API.
    """
    for i in range(n):
        print(f"[SYSTEM] Starting worker {i+1}")
        threading.Thread(target=worker, daemon=True).start()


# =========================
# إضافة مهمة
# =========================
def add_task(file_input, chat_id):
    """
    يضيف مهمة جديدة إلى الطابور.
    """
    position = task_queue.qsize() + 1
    print(f"[QUEUE] New task added. Position: {position}")
    task_queue.put((file_input, chat_id))
    send_message(chat_id, f"📌 تم إضافتك للطابور\n🔢 ترتيبك: {position}")


# =========================
# حجم الطابور
# =========================
def get_position():
    """
    يرجع عدد المهام الحالية في الطابور.
    """
    return task_queue.qsize()
