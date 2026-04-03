import fitz
import os
import urllib.request
import json
import re
import time

from config import TOKEN
from ai_service import call_ai_headers


# =========================
# 🔥 RATE CONTROL (HEADER BASED)
# =========================
SAFE_MARGIN = 1000
remaining_tokens = 999999
window_start = time.time()
remaining_requests = 999999
SAFE_REQUEST_MARGIN = 5

def wait_if_needed():
    global remaining_tokens, window_start

    if remaining_tokens < SAFE_MARGIN:
        print("⚠️ قريب من limit")

        elapsed = time.time() - window_start
        wait_time = max(0, 60 - elapsed)

        print(f"⏳ انتظار {wait_time:.1f} ثانية...")
        time.sleep(wait_time)

        window_start = time.time()


def update_limits(headers):
    global remaining_tokens, remaining_requests

    if "x-ratelimit-remaining-tokens" in headers:
        remaining_tokens = int(headers["x-ratelimit-remaining-tokens"])
        print(f"[TOKENS LEFT] {remaining_tokens}")

    if "x-ratelimit-remaining-requests" in headers:
        remaining_requests = int(headers["x-ratelimit-remaining-requests"])
        print(f"[REQUESTS LEFT] {remaining_requests}")

REQUEST_COUNT = 0


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
# 🔥 ترجمة الصفحة
# =========================
def translate_page_json(text, page_num):
    global REQUEST_COUNT

    text = clean_text(text)

    lines = text.split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    if not lines:
        print(f"[EMPTY PAGE] {page_num}")
        return {"page": page_num, "lines": []}

    chunk_size = 8
    all_translations = []

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

        messages = [
            {"role": "system", "content": "Strict translator."},
            {"role": "user", "content": prompt}
        ]

        try:
            REQUEST_COUNT += 1
            print(f"[REQ] {REQUEST_COUNT} | Page {page_num}")

            # 🔥 قبل الإرسال
            wait_if_needed()

            result, headers = call_ai_headers(
                messages,
                model="openai/gpt-oss-120b",
                temperature=0.1,
                max_tokens=1000
            )

            # 🔥 بعد الإرسال
            update_limits(headers)

        except Exception as e:
            print("AI Error:", e)
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
