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
- No questions.
- No question marks.
- Do not write answers.
- Do not write True or False.
- Number clearly (1, 2, 3...).
"""

        # ===============================
        # MULTIPLE CHOICE
        # ===============================
        elif is_mcq:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} أسئلة اختيار من متعدد.

- كل سؤال يحتوي على 4 خيارات فقط.
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

Format exactly:

1) Question
A) Option
B) Option
C) Option
D) Option
"""

        else:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} أسئلة {question_type}.

- بدون إجابات.
- بدون شرح.
- رتبها 1، 2، 3...
"""
            else:
                prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} {question_type} questions.

- No answers.
- No explanations.
- Number clearly.
"""

        messages = [
            {"role": "system", "content": "You generate exam content strictly following formatting rules."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=1000
        )

        forbidden = ["Answer", "الإجابة", "True", "False", "صح", "خطأ"]

        if any(word in result for word in forbidden):
            result = call_ai(
                messages,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1000
            )

        return result

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الامتحان."


# ===============================
# Generate Explanation (Cleaned)
# ===============================

def generate_explanation(pdf_path, start_page, end_page):

    try:
        content = get_content(pdf_path, start_page, end_page)

        if not content or len(content.strip()) < 20:
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        content = content[:2800]

        prompt = f"""
Based strictly and only on the following academic content:

{content}

1) Extract only meaningful conceptual headings.
2) Ignore numeric section labels (1.3, 1.4, etc.).
3) Remove duplicated headings.
4) Merge headings containing (Cont.) with the main heading.
5) Write each heading once in English only.
6) Under each heading write a clear Arabic explanation.
7) Use only the provided content.
8) Do not repeat sentences.

No Markdown.
Clean structure.
"""

        messages = [
            {"role": "system", "content": "You are a strict academic editor that removes duplication."},
            {"role": "user", "content": prompt}
        ]

        return call_ai(
            messages,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_tokens=1500
        )

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

Extract the most important subject-related terms only.

- Terms only.
- No explanations.
- No definitions.
- No numbering required.
"""

        messages = [
            {"role": "system", "content": "You extract academic terminology only."},
            {"role": "user", "content": prompt}
        ]

        return call_ai(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=600
        )

    except Exception as e:
        print("TERMS ERROR:", e)
        return "حدث خطأ أثناء استخراج المصطلحات."
