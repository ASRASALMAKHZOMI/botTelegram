import fitz
import os
import urllib.request
import json
import time
import re

from config import TOKEN
from ai_service import call_ai


# =========================
# تحميل ملف من تيليجرام
# =========================
def download_file(file_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode("utf-8"))

    file_path = data["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    os.makedirs("downloads", exist_ok=True)
    local_path = "downloads/" + os.path.basename(file_path)

    urllib.request.urlretrieve(download_url, local_path)
    return local_path


# =========================
# تحقق PDF
# =========================
def is_pdf(file_path):
    return file_path.lower().endswith(".pdf")


def is_scanned(file_path):
    doc = fitz.open(file_path)
    for page in doc:
        if page.get_text().strip():
            return False
    return True


# =========================
# تنظيف النص
# =========================
def clean_text(text):
    lines = text.split("\n")
    cleaned = []
    seen = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # حذف الرموز الغريبة
        if re.search(r"[?]{2,}", line):
            continue
        
        # حذف سطور قصيرة جداً
        if len(line) <= 2:
            continue

        # منع التكرار
        normalized = re.sub(r'\s+', ' ', line.lower())
        if normalized in seen:
            continue
        seen.add(normalized)

        # استبدال الرموز الخاصة
        line = (
            line.replace("", "-")
            .replace("", "-")
            .replace("•", "-")
            .replace("▶", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("ﬁ", "fi")
            .replace("ﬂ", "fl")
        )
        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# تقسيم الصفحات
# =========================
def split_pages_into_batches(doc, batch_size=4):
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append((i + 1, text))

    total = len(pages)
    batches = []
    i = 0

    while i < total:
        remaining = total - i
        if remaining < batch_size:
            half = remaining // 2
            if half == 0:
                batches.append(pages[i:])
            else:
                batches.append(pages[i:i+half])
                batches.append(pages[i+half:i+remaining])
            break
        else:
            batches.append(pages[i:i+batch_size])
            i += batch_size
    return batches


# =========================
# 🔥 ترجمة batch (النسخة النهائية مع Fallback)
# =========================
def translate_batch(pages):
    combined_text = ""
    for page_num, text in pages:
        combined_text += f"\n📄 الصفحة {page_num}\n{text}\n"

    combined_text = clean_text(combined_text)

    prompt = f"""
أنت مترجم متخصص في علوم الحاسوب.
ترجم النص التالي ترجمة تقنية دقيقة:
- كل سطر وتحته ترجمته
- لا تكرر النص
- لا تدمج الصفحات
- لا تغير "📄 الصفحة X"
- استخدم مصطلحات برمجية صحيحة
- حافظ على التنسيق
- لا تترجم الأكواد البرمجية
- لا تعكس ترتيب النص الإنجليزي
- اترك الكود كما هو

النص:
{combined_text}
"""

    messages = [
        {"role": "system", "content": "مترجم تقني دقيق."},
        {"role": "user", "content": prompt}
    ]

    # =========================
    # 🔥 Retry Logic محسن مع Exponential Backoff
    # =========================
    attempt = 0
    max_retries = 5

    while attempt < max_retries:
        try:
            result = call_ai(messages)

            if result and result.strip():
                return result
            else:
                raise Exception("Empty response from AI")

        except Exception as e:
            error_str = str(e)
            print(f"[BATCH ERROR {attempt + 1}/{max_retries}]: {error_str}")

            # 🔥 التعامل الذكي مع 429 (انتظار أطول مع كل محاولة)
            if "429" in error_str or "Too Many Requests" in error_str:
                # محاولة 1: 5 ثواني، محاولة 2: 10 ثواني، محاولة 3: 20 ثانية...
                wait = (2 ** attempt) * 5 
                print(f"[RATE LIMIT HIT] Waiting for {wait}s before retry...")
            else:
                wait = 3  # للأخطاء الأخرى ننتظر وقتاً قصيراً

            time.sleep(wait)
            attempt += 1

    # =========================
    # 🔥 Fallback: إرجاع النص الأصلي إذا فشلت كل المحاولات
    # =========================
    print("[FALLBACK] using original text")
    
    fallback = ""
    for page_num, text in pages:
        fallback += f"\n📄 الصفحة {page_num}\n{text}\n"
    
    return fallback  # ✅ نرجع النص الأصلي لضمان استمرار العملية
