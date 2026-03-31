import fitz
import os
import urllib.request
import json
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
# 🔥 فلترة النص بعد الترجمة
# =========================
def clean_translation_line(line):

    # حذف delimiter
    line = line.replace("|||SEP|||", "").strip()

    # حذف junk lines
    if len(line) < 2:
        return None

    # حذف كلمات غريبة جدًا
    if re.search(r"[^\w\s\u0600-\u06FF.,:;()\-\"']", line) and len(line) < 4:
        return None

    return line


# =========================
# 🔥 ترجمة الصفحة (Ultra Clean)
# =========================
def translate_page_json(text, page_num):

    text = clean_text(text)

    lines = text.split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    if not lines:
        return {"page": page_num, "lines": []}

    DELIM = "|||SEP|||"
    chunk_size = 10

    all_translations = []

    for i in range(0, len(lines), chunk_size):

        chunk = lines[i:i + chunk_size]

        joined = f"\n{DELIM}\n".join(chunk)

        prompt = f"""
Translate each segment to Arabic professionally.

Each segment is separated by: {DELIM}

IMPORTANT:
- Return SAME delimiter
- Keep SAME number of segments
- Do NOT merge or skip
- Use proper technical Arabic
- Avoid random words or mixed languages

TEXT:
{joined}
"""

        messages = [
            {"role": "system", "content": "Professional technical translator."},
            {"role": "user", "content": prompt}
        ]

        try:
            result = call_ai(
                messages,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1000
            )
        except Exception as e:
            print("AI Error:", e)
            return None

        if not result:
            return None

        translated = result.split(DELIM)
        translated = [clean_translation_line(l) for l in translated]
        translated = [l if l is not None else "" for l in translated]

        # 🔥 AUTO FIX
        if len(translated) != len(chunk):
            print("Mismatch fixing...")

            if len(translated) < len(chunk):
                translated += [""] * (len(chunk) - len(translated))
            else:
                translated = translated[:len(chunk)]

        all_translations.extend(translated)

    # بناء JSON
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
# 🔥 دمج نظيف (Smart Merge)
# =========================
def format_page_from_json(page_data):

    output = []
    seen = set()

    for item in page_data["lines"]:

        en = item["en"].strip()
        ar = item["ar"].strip()

        # حذف delimiter
        if "|||SEP|||" in en:
            continue

        # حذف التكرار (ذكي)
        key = en.lower()
        if key in seen:
            continue
        seen.add(key)

        # حذف junk
        if len(en) < 2:
            continue

        # دمج نظيف
        output.append(en)
        output.append(ar)
        output.append("")

    # تنظيف نهائي
    final_text = "\n".join(output)

    # إزالة الفراغات الزائدة
    final_text = re.sub(r"\n{3,}", "\n\n", final_text)

    return final_text


# =========================
# حفظ JSON
# =========================
def save_page_json(page_data):

    os.makedirs("json_pages", exist_ok=True)

    path = f"json_pages/page_{page_data['page']}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)
