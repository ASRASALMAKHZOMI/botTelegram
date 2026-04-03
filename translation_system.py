import fitz
import os
import urllib.request
import json
import re
import time

from config import TOKEN
from ai_service import call_ai_gemini


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

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# تنظيف الترجمة
# =========================
def clean_translation_line(line):

    line = line.strip()

    line = re.sub(r"\[\d+\]", "", line)
    line = line.replace("|||SEP|||", "")

    if len(line) < 2:
        return ""

    return line


# =========================
# 🔥 ترجمة الصفحة (Gemini)
# =========================
def translate_page_json(text, page_num):

    text = clean_text(text)

    lines = text.split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    if not lines:
        print(f"[EMPTY PAGE] {page_num}")
        return {"page": page_num, "lines": []}

    chunk_size = 30  # ✅ 30 سطر
    all_translations = []
    REQUEST_COUNT = 0

    for i in range(0, len(lines), chunk_size):

        chunk = lines[i:i + chunk_size]

        indexed_lines = []
        for idx, line in enumerate(chunk):
            indexed_lines.append(f"[{idx}] {line}")

        joined = "\n".join(indexed_lines)

        prompt = f"""
Translate each line to Arabic.

IMPORTANT:
- Keep the SAME numbering
- Do NOT merge lines
- Do NOT skip lines
- Do NOT add explanations
- Return EXACT format:

[0] translation
[1] translation

TEXT:
{joined}
"""

        try:
            REQUEST_COUNT += 1
            print(f"[REQ] {REQUEST_COUNT} | Page {page_num}")

            # ⏳ انتظار 4 ثواني
            time.sleep(4)

            result = call_ai_gemini(prompt, temperature=0.1)

        except Exception as e:
            print("Gemini Error:", e)
            return None

        if not result:
            return None

        # =========================
        # PARSE
        # =========================
        translated_lines = result.split("\n")
        parsed = {}

        for line in translated_lines:
            match = re.match(r"\[(\d+)\]\s*(.*)", line)
            if match:
                index = int(match.group(1))
                translated_text = clean_translation_line(match.group(2))
                parsed[index] = translated_text

        fixed = []
        for idx in range(len(chunk)):
            fixed.append(parsed.get(idx, ""))

        all_translations.extend(fixed)

    # =========================
    # JSON
    # =========================
    page_data = {
        "page": page_num,
        "lines": []
    }

    for en, ar in zip(lines, all_translations):
        page_data["lines"].append({
            "en": en,
            "ar": ar
        })

    return page_data


# =========================
# دمج
# =========================
def format_page_from_json(page_data):

    output = []
    seen = set()

    for item in page_data["lines"]:

        en = item["en"].strip()
        ar = item["ar"].strip()

        key = en.lower()

        if key in seen:
            continue
        seen.add(key)

        output.append(en)
        output.append(ar)
        output.append("")

    return "\n".join(output)


# =========================
# حفظ JSON
# =========================
def save_page_json(page_data):

    os.makedirs("json_pages", exist_ok=True)

    path = f"json_pages/page_{page_data['page']}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)
