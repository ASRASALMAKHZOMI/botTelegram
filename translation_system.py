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

    lines = text.split("\n")
    cleaned = []
    seen = set()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # إزالة التكرار
        if line in seen:
            continue
        seen.add(line)

        # تنظيف الرموز
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

        # حذف النص التالف
        if "????" in line:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# تقسيم الصفحات إلى batches
# =========================
def split_pages_into_batches(doc, batch_size=4):

    batches = []
    current = []

    for i, page in enumerate(doc):

        text = page.get_text().strip()

        if not text:
            continue

        current.append((i + 1, text))

        if len(current) == batch_size:
            batches.append(current)
            current = []

    if current:
        batches.append(current)

    return batches


# =========================
# ترجمة batch (عدة صفحات)
# =========================
def translate_batch(pages):

    combined_text = ""

    for page_num, text in pages:
        combined_text += f"\n📄 الصفحة {page_num}\n{text}\n"

    combined_text = clean_text(combined_text)

    prompt = f"""
أنت مترجم متخصص في علوم الحاسوب.

ترجم النص التالي ترجمة تقنية دقيقة:

⚠️ تعليمات:
- كل سطر وتحته ترجمته
- لا تكرر النص
- لا تدمج الصفحات
- لا تغير "📄 الصفحة X"
- استخدم مصطلحات برمجية صحيحة
- حافظ على التنسيق

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
                time.sleep(2)  # تهدئة لتجنب 429
                return result

        except Exception as e:
            print(f"[BATCH RETRY {attempt}] ERROR:", e)

            wait = min(10, 2 + attempt)
            time.sleep(wait)

            attempt += 1
