import os
import json
import fitz  # PyMuPDF
from ai_service import call_ai

STORAGE_FILE = "exam_storage.json"


# =========================
# تحميل / حفظ التخزين
# =========================
def load_storage():
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_storage(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# استخراج نص من نطاق صفحات
# =========================
def extract_text_from_pdf(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)
    text = ""

    total_pages = len(doc)

    start_page = max(1, start_page)
    end_page = min(total_pages, end_page)

    for page_num in range(start_page - 1, end_page):
        text += doc[page_num].get_text()

    return text


# =========================
# جلب المحتوى أو إنشاؤه
# =========================
def get_content(level, subject, pdf_path, start_page, end_page):
    key = f"{level}|{subject}|{start_page}-{end_page}"

    storage = load_storage()

    if key in storage:
        return storage[key]["content"]

    text = extract_text_from_pdf(pdf_path, start_page, end_page)

    storage[key] = {
        "content": text
    }

    save_storage(storage)

    return text


# =========================
# توليد الأسئلة
# =========================
def generate_exam(level, subject, pdf_path, start_page, end_page, question_type, count):

    content = get_content(level, subject, pdf_path, start_page, end_page)

    prompt = f"""
    من النص التالي:

    {content[:4000]}

    أنشئ {count} أسئلة من نوع {question_type}.

    الشروط:
    - لا تستخدم Markdown
    - لا تستخدم رموز نجوم
    - تنسيق واضح
    - اكتب:
      السؤال 1:
      السؤال 2:
      وهكذا
    """

    messages = [
        {"role": "system", "content": "أنت خبير إعداد أسئلة امتحانية جامعية."},
        {"role": "user", "content": prompt}
    ]

    return call_ai(messages)