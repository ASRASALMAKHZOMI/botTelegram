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
# تقسيم النص
# =========================
def split_big_text(text, size=3500):
    return [text[i:i+size] for i in range(0, len(text), size)]


# =========================
# ترجمة صفحة كاملة
# =========================
def translate_page(page_text):

    chunks = split_big_text(page_text, 3500)
    results = []

    for chunk in chunks:

        chunk = clean_text(chunk)

        if len(chunk.strip()) < 3:
            continue

        for attempt in range(3):  # 🔥 retry

            try:
                prompt = f"""
ترجم النص التالي إلى العربية سطر بسطر:

- كل سطر وتحته ترجمته
- نفس الترتيب
- لا تدمج
- لا تحذف
- تجاهل الأكواد البرمجية

النص:
{chunk}
"""

                messages = [
                    {"role": "system", "content": "مترجم تقني دقيق."},
                    {"role": "user", "content": prompt}
                ]

                result = call_ai(messages)

                if result:
                    results.append(result)
                    break

            except Exception as e:
                print("Retry...", e)
                time.sleep(2)

        time.sleep(1)  # 🔥 يمنع 429

    return "\n".join(results)


# =========================
# النظام الكامل
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
