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

        # ===============================
        # فحص إذا الملف سكانر (لا يوجد نص)
        # ===============================
        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر (صور فقط).\n\nلا يمكن استخراج نص لإنشاء أسئلة."

        # ===============================
        # تحديد لغة المحتوى (عربي أو إنجليزي)
        # ===============================
        arabic_chars = sum(1 for c in content if '\u0600' <= c <= '\u06FF')
        english_chars = sum(1 for c in content if c.isascii())

        if arabic_chars > english_chars:
            language = "arabic"
        else:
            language = "english"

        # ===============================
        # تحويل نوع السؤال
        # ===============================
        type_map_en = {
            "صح وخطأ": "True/False",
            "اختيار من متعدد": "Multiple Choice",
            "مقالي": "Essay"
        }

        type_map_ar = {
            "صح وخطأ": "صح أو خطأ",
            "اختيار من متعدد": "اختيار من متعدد",
            "مقالي": "مقالية"
        }

        if language == "arabic":
            question_type_final = type_map_ar.get(question_type, question_type)
        else:
            question_type_final = type_map_en.get(question_type, question_type)

        # ===============================
        # بناء البرومبت حسب اللغة
        # ===============================
        if language == "arabic":

            prompt = f"""
بناءً على المحتوى التالي:

{content[:3500]}

قم بإنشاء {count} أسئلة {question_type_final}.

الشروط:
- جميع الأسئلة يجب أن تكون باللغة العربية.
- لا تستخدم Markdown.
- تنسيق واضح.
- ابدأ بالضبط بـ:
السؤال 1:
"""

        else:

            prompt = f"""
Based on the following content:

{content[:3500]}

Generate {count} {question_type_final} exam questions.

Requirements:
- All questions must be in English.
- Do not use Markdown.
- Clear formatting.
- Start exactly with:
Question 1:
"""

        messages = [
            {"role": "system", "content": "You are a professional university exam creator."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(messages)

        if not result:
            return "حدث خطأ أثناء إنشاء الأسئلة."

        return result

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الامتحان."
