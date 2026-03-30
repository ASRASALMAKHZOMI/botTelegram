import fitz
import os
import urllib.request
import json

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
# استخراج سطور من PDF
# =========================
def extract_lines(pdf_path):

    doc = fitz.open(pdf_path)
    lines = []

    for page in doc:
        text = page.get_text()

        for line in text.split("\n"):
            clean = line.strip()

            if clean:
                lines.append(clean)

    doc.close()
    return lines


# =========================
# ترجمة سطر واحد (Groq)
# =========================
def translate_line(line):

    prompt = f"""
ترجم السطر التالي إلى العربية فقط:

- ترجمة دقيقة
- بدون شرح
- بدون إضافة

النص:
{line}
"""

    messages = [
        {"role": "system", "content": "أنت مترجم محترف."},
        {"role": "user", "content": prompt}
    ]

    result = call_ai(messages)

    return result.strip() if result else ""


# =========================
# ترجمة كل الملف (سطر بسطر)
# =========================
def translate_to_text(pdf_path):

    lines = extract_lines(pdf_path)

    if not lines:
        raise Exception("لا يوجد نص داخل الملف")

    output = []

    for line in lines:

        # تجاهل السطور القصيرة جداً
        if len(line) < 2:
            continue

        try:
            translated = translate_line(line)

            output.append(f"{line}\n{translated}\n")

        except Exception as e:
            print("LINE ERROR:", e)
            output.append(f"{line}\n[خطأ في الترجمة]\n")

    return "\n".join(output)
