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

        if language == "arabic":
            prompt = f"""
بناءً على المحتوى التالي:

{content[:3500]}

أنشئ بالضبط {count} أسئلة {question_type}.
الشروط:
- باللغة العربية
- لا تستخدم Markdown
- لا تضف أي شرح خارج الأسئلة
"""
        else:
            prompt = f"""
Based on the following content:

{content[:3500]}

Generate exactly {count} {question_type} questions.
Requirements:
- English language
- No markdown
- No extra explanations
"""

        messages = [
            {"role": "system", "content": "You are a professional university exam creator."},
            {"role": "user", "content": prompt}
        ]

        # يستخدم نفس الموديل الافتراضي (مثلاً 120B عندك)
        result = call_ai(messages, temperature=0.5, max_tokens=1000)

        return result

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الامتحان."


# ===============================
# Generate Explanation
# ===============================

def generate_explanation(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        arabic_chars = sum(1 for c in content if '\u0600' <= c <= '\u06FF')
        english_chars = sum(1 for c in content if c.isascii())

        language = "arabic" if arabic_chars > english_chars else "english"

        if language == "english":
            prompt = f"""
Based on the following academic content:

{content[:3500]}

Do the following:

1) Extract the most important technical terms in English.
2) For each term:
   - Write the term in English.
   - Explain it clearly in Arabic.
3) Provide a concise Arabic summary in bullet points.

Rules:
- No Markdown
- Maximum 600 words
"""
        else:
            prompt = f"""
بناءً على المحتوى التالي:

{content[:3500]}

قم بما يلي:

1) اكتب شرحاً منظماً وواضحاً.
2) استخرج أهم المصطلحات وعرّفها باختصار.
3) اكتب ملخص نقاط سريع للمراجعة.

الشروط:
- بدون Markdown
- لا يتجاوز 600 كلمة
"""

        messages = [
            {"role": "system", "content": "You are a professional academic explainer."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.4,
            max_tokens=600
        )

        return result

    except Exception as e:
        print("EXPLANATION ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الشرح."


# ===============================
# Generate Subject Terms
# ===============================

def generate_terms(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        prompt = f"""
Based on the following academic content:

{content[:3500]}

Extract the most important subject-related terms.

For each term:
- Write the term in English.
- Provide a short explanation in Arabic.

Rules:
- Organized list
- No Markdown
- Maximum 40 terms
"""

        messages = [
            {"role": "system", "content": "You are an academic terminology expert."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=500
        )

        return result

    except Exception as e:
        print("TERMS ERROR:", e)
        return "حدث خطأ أثناء استخراج المصطلحات."
