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
# Split Large Content
# ===============================

def split_content(text, chunk_size=1200):
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]


# ===============================
# Generate Exam
# ===============================

def generate_exam(pdf_path, start_page, end_page, question_type, count):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        content = content[:2500]
        language = detect_language(content)

        qt = question_type.lower()
        is_true_false = "true" in qt or "صح" in qt
        is_mcq = "choice" in qt or "اخت" in qt or "mcq" in qt

        # ===============================
        # TRUE / FALSE
        # ===============================
        if is_true_false:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} عبارات صح وخطأ.

- عبارات خبرية فقط.
- لا تكتب سؤال.
- لا تستخدم علامة استفهام.
- لا تكتب الإجابة.
- لا تكتب (صح) أو (خطأ).
- رتبها 1، 2، 3...
"""
            else:
                prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} True/False statements.

- Declarative statements only.
- No question marks.
- Do not write answers.
- Do not write True or False.
- Number clearly.
"""

            max_tokens = 900

        # ===============================
        # MULTIPLE CHOICE
        # ===============================
        elif is_mcq:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} أسئلة اختيار من متعدد.

- كل سؤال يحتوي 4 خيارات فقط.
- لا تكتب الإجابة الصحيحة.
- لا تضع علامة صح.
- لا تضف شرح.
- التنسيق:

1) نص السؤال
A) خيار
B) خيار
C) خيار
D) خيار
"""
            else:
                prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} multiple choice questions.

- Each question must have exactly 4 options.
- Do NOT write the correct answer.
- Do NOT mark the correct option.
- No explanations.

Format:

1) Question
A) Option
B) Option
C) Option
D) Option
"""

            max_tokens = 1200   # تم تقليلها من 1600 لتحسين الأداء

        # ===============================
        # OTHER TYPES
        # ===============================
        else:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} أسئلة {question_type}.
بدون إجابات.
"""
            else:
                prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} {question_type} questions.
No answers.
"""

            max_tokens = 1000

        messages = [
            {"role": "system", "content": "You strictly follow formatting rules and never provide answers."},
            {"role": "user", "content": prompt}
        ]

        return call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=max_tokens
        )

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الامتحان."


# ===============================
# Generate Explanation (Chunked Stable Version)
# ===============================

def generate_explanation(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        # تقسيم المحتوى + حد أقصى 5 أجزاء
        chunks = split_content(content, 1200)[:5]

        final_result = ""

        for index, chunk in enumerate(chunks):

            prompt = f"""
Based strictly and only on the following academic content:

{chunk}

1) Extract conceptual headings only.
2) For each heading:
   - Write heading in English.
   - Then Arabic explanation.
3) Keep explanation concise.
4) Do not invent information.
5) No Markdown.
"""

            messages = [
                {"role": "system", "content": "You are a strict academic explainer."},
                {"role": "user", "content": prompt}
            ]

            part = call_ai(
                messages,
                model="llama-3.1-8b-instant",
                temperature=0.15,
                max_tokens=1000
            )

            if part:
                final_result += part + "\n\n"

        return final_result.strip()

    except Exception as e:
        print("EXPLANATION ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الشرح."


# ===============================
# Generate Terms
# ===============================

def generate_terms(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        content = content[:2500]

        prompt = f"""
Based on the following academic content:

{content}

Extract important subject-related terms only.
No explanations.
Maximum 50 terms.
"""

        messages = [
            {"role": "system", "content": "You extract terminology only."},
            {"role": "user", "content": prompt}
        ]

        return call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=700
        )

    except Exception as e:
        print("TERMS ERROR:", e)
        return "حدث خطأ أثناء استخراج المصطلحات."
