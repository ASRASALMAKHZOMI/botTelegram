import fitz
import os
import urllib.request
import json
import time

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
    import re

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

        # حذف سطور قصيرة غريبة
        if len(line) <= 2:
            continue

        # توحيد للمقارنة
        normalized = re.sub(r'\s+', ' ', line.lower())

        if normalized in seen:
            continue

        seen.add(normalized)

        # تنظيف
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
# تقسيم الصفحات (Balanced بدون دمج)
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

        # 🔥 إذا بقي صفحات قليلة → نقسمها بالتساوي
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
# ترجمة batch
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

    attempt = 0

    while True:
        try:
            result = call_ai(messages)

            if result:
                time.sleep(2)
                return result

        except Exception as e:
            print(f"[BATCH ERROR {attempt}]:", e)

            wait = min(10, 2 + attempt)
            time.sleep(wait)

            attempt += 1
