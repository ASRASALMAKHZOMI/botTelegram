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
# Detect Language
# ===============================

def detect_language(text):
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    english_chars = sum(1 for c in text if c.isalpha() and c.isascii())
    return "arabic" if arabic_chars > english_chars else "english"


# ===============================
# Generate Exam Questions
# ===============================

def generate_exam(pdf_path, start_page, end_page, question_type, count):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر (صور فقط).\n\nلا يمكن استخراج نص لإنشاء أسئلة."

        content = content[:3000]
        language = detect_language(content)

        if language == "arabic":
            prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} أسئلة {question_type}.

الشروط:
- رتب الأسئلة ترقيمياً (1، 2، 3 ...)
- لا تستخدم Markdown
- لا تضف أي شرح خارج نص السؤال
- لا تكرر نفس الفكرة
- التزم بالمحتوى فقط
-لا تحل السؤال
"""
        else:
            prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} {question_type} questions.

Requirements:
- Number them clearly (1, 2, 3 ...)
- No markdown
- No explanations outside the questions
- No repetition
- Use only the provided content
"""

        messages = [
            {"role": "system", "content": "You are a precise university exam creator."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            temperature=0.4,
            max_tokens=1400
        )

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

        content = content[:3000]

        prompt = f"""
Based strictly and only on the following academic content:

{content}

Instructions:

1) Extract the subheadings exactly as they appear.
2) Write each subheading in English.
3) Under each subheading:
   - Provide a clear Arabic explanation.
   - The explanation must be derived ONLY from the given content.
   - Do not add any external knowledge.
   - Expand slightly for clarity without exceeding the source ideas.

Rules:
- Preserve structure.
- Keep it organized.
- No Markdown.
- Do not invent information.
"""

        messages = [
            {"role": "system", "content": "You are a strict academic explainer that follows the source exactly."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            temperature=0.2,
            max_tokens=1500
        )

        return result

    except Exception as e:
        print("EXPLANATION ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الشرح."


# ===============================
# Generate Subject Terms (بدون شرح)
# ===============================

def generate_terms(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        content = content[:3000]

        prompt = f"""
Based on the following academic content:

{content}

Extract the most important subject-related terms only.

Rules:
- List only the terms.
- No explanations.
- No definitions.
- No Markdown.
- Maximum 50 terms.
"""

        messages = [
            {"role": "system", "content": "You are an academic terminology extractor."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=600
        )

        return result

    except Exception as e:
        print("TERMS ERROR:", e)
        return "حدث خطأ أثناء استخراج المصطلحات."

