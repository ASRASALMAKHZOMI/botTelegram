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
        text = page.get_text("text", sort=True).strip()
        if text:
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

        # حذف التكرار فقط لو مكرر فعلاً بشكل مزعج
        if line in seen:
            continue
        seen.add(line)

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

        if "????" in line:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# تقسيم الصفحات (ذكي)
# =========================
def split_pages_into_batches(doc, batch_size=4):

    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text", sort=True).strip()

        # fallback لو فاضي
        if not text:
            blocks = page.get_text("blocks")
            text = "\n".join([b[4] for b in blocks if b[4].strip()])

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
                batches.append(pages[i:i + half])
                batches.append(pages[i + half:i + remaining])

            break

        batch = pages[i:i + batch_size]
        batches.append(batch)
        i += batch_size

    return batches


# =========================
# ترجمة صفحة واحدة (مهم جداً)
# =========================
def translate_page(text):

    text = clean_text(text)

    if not text.strip():
        return "(صفحة فارغة)"

    prompt = f"""
أنت مترجم متخصص في علوم الحاسوب.

ترجم النص التالي ترجمة دقيقة:

⚠️ مهم جداً:
- ترجم كل سطر مهما كان قصير
- حتى لو كان نقطة أو كلمة
- لا تترك أي سطر بدون ترجمة إطلاقاً
- لا تختصر
- لا تشرح
- استخدم مصطلحات تقنية صحيحة

النص:
{text}
"""

    messages = [
        {"role": "system", "content": "مترجم تقني صارم."},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(5):
        try:
            result = call_ai(messages)

            if result and result.strip():
                time.sleep(2)
                return result

        except Exception as e:
            print("Retry page...", e)

        time.sleep(2 + attempt)

    return text


# =========================
# ترجمة batch (محسن)
# =========================
def translate_batch(pages):

    combined_text = ""

    for page_num, text in pages:
        combined_text += f"\n📄 الصفحة {page_num}\n{text}\n"

    combined_text = clean_text(combined_text)

    # 🔥 لو النص قصير → لا تستخدم batch
    if len(combined_text) < 800:
        return None

    prompt = f"""
أنت مترجم تقني محترف.

ترجم النص التالي:

⚠️ قواعد صارمة:
- لا تترك أي سطر بدون ترجمة
- حتى النقاط القصيرة ترجمها
- لا تدمج الصفحات
- لا تغير "📄 الصفحة X"
- حافظ على نفس ترتيب النص
- لا تختصر

النص:
{combined_text}
"""

    messages = [
        {"role": "system", "content": "مترجم تقني دقيق جداً."},
        {"role": "user", "content": prompt}
    ]

    attempt = 0

    while True:
        try:
            result = call_ai(messages)

            if result and result.strip():
                time.sleep(3)
                return result

        except Exception as e:
            print(f"[BATCH ERROR {attempt}]:", e)

        wait = min(20, 3 + attempt * 2)
        time.sleep(wait)

        attempt += 1

        if attempt >= 5:
            return None
