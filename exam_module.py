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
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    start_page = max(1, start_page)
    end_page = min(total_pages, end_page)

    text = ""
    for i in range(start_page - 1, end_page):
        text += doc[i].get_text()

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
    content = get_content(pdf_path, start_page, end_page)

    prompt = f"""
    من المحتوى التالي:

    {content[:4000]}

    أنشئ {count} أسئلة من نوع {question_type}.

    بدون Markdown
    بدون نجوم
    تنسيق واضح
    ابدأ بـ:
    السؤال 1:
    """

    messages = [
        {"role": "system", "content": "أنت خبير إعداد اختبارات جامعية."},
        {"role": "user", "content": prompt}
    ]

    return call_ai(messages)
