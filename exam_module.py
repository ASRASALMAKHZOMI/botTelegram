import os
import json
import fitz
from ai_service import call_ai

STORAGE_FILE = "exam_storage.json"


# ===============================
# Storage Helpers
# ===============================

def load_storage():
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_storage(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===============================
# Extract Text From PDF
# ===============================

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


# ===============================
# Generate Exam Questions
# ===============================

def generate_exam(pdf_path, start_page, end_page, question_type, count):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر (صور فقط).\n\nلا يمكن استخراج نص لإنشاء أسئلة."

        arabic_chars = sum(1 for c in content if '\u0600' <= c <= '\u06FF')
        english_chars = sum(1 for c in content if c.isascii())

        language = "arabic" if arabic_chars > english_chars else "english"

        type_map_en = {
            "صح أو خطأ": "True/False",
            "اختياري": "Multiple Choice"
        }

        type_map_ar = {
            "صح أو خطأ": "صح أو خطأ",
            "اختياري": "اختيار من متعدد"
        }

        question_type_final = (
            type_map_ar.get(question_type, question_type)
            if language == "arabic"
            else type_map_en.get(question_type, question_type)
        )

        if language == "arabic":

            prompt = f"""
بناءً على المحتوى التالي:

{content[:3500]}

أنشئ بالضبط {count} أسئلة {question_type_final}.

الشروط:
- باللغة العربية
- لا تستخدم Markdown
- لا تضف أي شرح خارج الأسئلة
"""

        else:

            prompt = f"""
Based on the following content:

{content[:3500]}

Generate exactly {count} {question_type_final} questions.

Requirements:
- English language
- No markdown
- No extra explanations
"""

        messages = [
            {"role": "system", "content": "You are a professional university exam creator."},
            {"role": "user", "content": prompt}
        ]

        # 👇 نستخدم موديل متوسط لتقليل التكلفة
        result = call_ai(
            messages,
            model="openai/gpt-oss-20b",
            temperature=0.5,
            max_tokens=1000
        )

        if not result:
            return "حدث خطأ أثناء إنشاء الأسئلة."

        return result

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الامتحان."


# ===============================
# Generate Explanation (جديد)
# ===============================

def generate_explanation(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        arabic_chars = sum(1 for c in content if '\u0600' <= c <= '\u06FF')
        english_chars = sum(1 for c in content if c.isascii())

        language = "arabic" if arabic_chars > english_chars else "english"

        if language == "arabic":
            prompt = f"""
بناءً على المحتوى التالي:

{content[:3500]}

اكتب شرحاً منظماً وواضحاً للموضوع.
الشروط:
- باللغة العربية
- منظم بعناوين واضحة
- بدون Markdown
- بدون أسئلة
- لا يتجاوز 500 كلمة
"""
        else:
            prompt = f"""
Based on the following content:

{content[:3500]}

Write a structured explanation.
Requirements:
- English
- Organized sections
- No markdown
- No questions
- Maximum 500 words
"""

        messages = [
            {"role": "system", "content": "You are a professional academic explainer."},
            {"role": "user", "content": prompt}
        ]

        # 👇 موديل أرخص جداً لتقليل الاستهلاك
        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.4,
            max_tokens=900
        )

        if not result:
            return "حدث خطأ أثناء إنشاء الشرح."

        return result

    except Exception as e:
        print("EXPLANATION ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الشرح."
