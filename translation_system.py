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
# تنظيف النص (🔥 مهم)
# =========================
def clean_text(text):
    return (
        text.replace("▶", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
    )


# =========================
# ترجمة صفحة واحدة (🔥 أهم جزء)
# =========================
def translate_page(page_text):

    page_text = clean_text(page_text)

    if not page_text.strip():
        return ""

    prompt = f"""
ترجم النص التالي إلى العربية سطر بسطر:

- كل سطر وتحته ترجمته
- نفس الترتيب
- لا تدمج السطور
- لا تحذف شيء
- لا تضف شرح
- تجاهل الأكواد البرمجية

النص:
{page_text}
"""

    messages = [
        {"role": "system", "content": "أنت مترجم تقني دقيق."},
        {"role": "user", "content": prompt}
    ]

    # 🔥 retry + حماية من 429
    for attempt in range(5):
        try:
            result = call_ai(messages)

            if result:
                time.sleep(2)  # 🔥 مهم جدًا لتجنب 429
                return result

        except Exception as e:
            print("Retry...", e)
            time.sleep(3)

    return "[فشل الترجمة]"


# =========================
# ترجمة كامل الملف (اختياري)
# =========================
def translate_to_text(pdf_path):

    doc = fitz.open(pdf_path)
    final_output = []

    for i, page in enumerate(doc):

        page_number = i + 1
        text = page.get_text()

        if not text.strip():
            continue

        final_output.append(f"📄 الصفحة {page_number}\n")

        try:
            translated = translate_page(text)
            final_output.append(translated)

        except Exception as e:
            print("PAGE ERROR:", e)
            final_output.append("[خطأ]\n")

        final_output.append("\n\n")

    doc.close()

    return "\n".join(final_output)
