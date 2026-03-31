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
# 🔥 ترجمة الصفحة → JSON (بدون fallback)
# =========================
def translate_page_json(text, page_num):

    text = clean_text(text)

    lines = text.split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    if not lines:
        return {"page": page_num, "lines": []}

    # 🔥 delimiter ثابت
    DELIM = "|||SEP|||"

    joined = f"\n{DELIM}\n".join(lines)

    prompt = f"""
Translate each segment to Arabic.

Each segment is separated by: {DELIM}

VERY IMPORTANT:
- You MUST return the SAME delimiter: {DELIM}
- Do NOT remove or change it
- Keep SAME number of segments
- Do NOT merge segments
- Do NOT skip anything
- Return ONLY Arabic text

TEXT:
{joined}
"""

    messages = [
        {"role": "system", "content": "Strict translator."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=2000
        )
    except Exception as e:
        print("AI Error:", e)
        return None

    if not result:
        return None

    # 🔥 split باستخدام delimiter
    translated_lines = result.split(DELIM)
    translated_lines = [l.strip() for l in translated_lines if l.strip()]

    # تحقق صارم
    if len(translated_lines) != len(lines):
        print("Mismatch lines!")
        return None

    # بناء JSON
    page_data = {
        "page": page_num,
        "lines": []
    }

    for en, ar in zip(lines, translated_lines):
        page_data["lines"].append({
            "en": en,
            "ar": ar
        })

    return page_data


# =========================
# تنسيق JSON → نص (الكود يتحكم)
# =========================
def format_page_from_json(page_data):

    output = []

    for item in page_data["lines"]:
        output.append(item["en"])
        output.append(item["ar"])
        output.append("")

    return "\n".join(output)


# =========================
# حفظ JSON لكل صفحة
# =========================
def save_page_json(page_data):

    os.makedirs("json_pages", exist_ok=True)

    path = f"json_pages/page_{page_data['page']}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)
