import os
import json
import fitz
from ai_service import call_ai

STORAGE_FILE = "exam_storage.json"


def load_storage():
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_storage(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_text(pdf_path, start_page, end_page):

    if not os.path.exists(pdf_path):
        raise Exception("PDF file not found")

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if start_page > total_pages:
        raise Exception("Start page exceeds total pages")

    if end_page > total_pages:
        end_page = total_pages

    if start_page > end_page:
        raise Exception("Invalid page range")

    text = ""

    for i in range(start_page - 1, end_page):
        text += doc[i].get_text()

    doc.close()

    return text


def get_content(pdf_path, start_page, end_page):
    key = f"{pdf_path}|{start_page}-{end_page}"
    storage = load_storage()

    if key in storage:
        return storage[key]

    text = extract_text(pdf_path, start_page, end_page)
    storage[key] = text
    save_storage(storage)

    return text


def generate_exam(pdf_path, start_page, end_page, question_type, count):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "لم يتم استخراج نص من الصفحات المحددة."

        prompt = f"""
من المحتوى التالي:

{content[:3500]}

أنشئ {count} أسئلة من نوع {question_type}.

الشروط:
- بدون Markdown
- بدون نجوم
- بدون رموز غريبة
- تنسيق واضح
- ابدأ بـ:
السؤال 1:
"""

        messages = [
            {"role": "system", "content": "أنت خبير إعداد اختبارات جامعية."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(messages)

        if not result:
            return "حدث خطأ أثناء توليد الأسئلة."

        return result

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الاختبار."
