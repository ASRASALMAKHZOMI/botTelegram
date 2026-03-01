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
            return "❌ الملف يبدو أنه ممسوح بالسكانر."

        content = content[:2500]
        language = detect_language(content)

        is_true_false = "true" in question_type.lower() or "صح" in question_type

        # ===============================
        # TRUE / FALSE
        # ===============================
        if is_true_false:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} عبارات صح وخطأ.

قواعد صارمة:
- اكتب عبارات خبرية فقط.
- لا تكتب بصيغة سؤال.
- لا تستخدم علامة استفهام.
- لا تبدأ بـ ماذا أو هل أو لماذا.
- لا تكتب الإجابة.
- لا تكتب (صح) أو (خطأ).
- رتبها ترقيمياً (1، 2، 3 ...).
- العدد يجب أن يكون {count} بالضبط.
"""
            else:
                prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} True/False statements.

STRICT RULES:
- Write declarative statements only.
- Do NOT write questions.
- Do NOT use question marks.
- Do NOT start with What, Why, How, When.
- Do NOT write True or False.
- Do NOT include answers.
- Number clearly (1, 2, 3 ...).
- Must generate exactly {count} statements.
"""

        # ===============================
        # OTHER TYPES
        # ===============================
        else:

            if language == "arabic":
                prompt = f"""
بناءً فقط على المحتوى التالي:

{content}

أنشئ بالضبط {count} أسئلة {question_type}.

قواعد:
- اللغة العربية فقط.
- لا تضف شرح.
- لا تضف إجابات.
- لا تضف مقدمة أو خاتمة.
- رتب الأسئلة ترقيمياً.
- العدد يجب أن يكون {count}.
"""
            else:
                prompt = f"""
Based strictly on the following content:

{content}

Generate exactly {count} {question_type} questions.

Rules:
- English only.
- No explanations.
- No answers.
- No introduction or conclusion.
- Number clearly.
- Must generate exactly {count}.
"""

        messages = [
            {"role": "system", "content": "You generate exam content strictly following instructions."},
            {"role": "user", "content": prompt}
        ]

        result = call_ai(
            messages,
            model="llama-3.1-8b-instant",  # موديل رخيص لتقليل التكلفة
            temperature=0.2,
            max_tokens=900
        )

        # منع تسرب الإجابات
        forbidden = ["True", "False", "صح", "خطأ", "Answer", "الإجابة", "?"]

        if is_true_false and any(word in result for word in forbidden):
            result = call_ai(
                messages,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=900
            )

        return result

    except Exception as e:
        print("GENERATE EXAM ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الامتحان."


# ===============================
# Generate Explanation (من نفس الملزمة فقط)
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

1) Extract the subheadings exactly as written.
2) Write each subheading in English.
3) Under each subheading:
   - Provide a clear Arabic explanation.
   - Use only information from the content.
   - Expand slightly for clarity.
   - Do not add external knowledge.

No Markdown.
"""

        messages = [
            {"role": "system", "content": "You explain academic content strictly based on the source."},
            {"role": "user", "content": prompt}
        ]

        return call_ai(
            messages,
            model="openai/gpt-oss-120b",  # موديل أقوى للشرح
            temperature=0.2,
            max_tokens=1500
        )

    except Exception as e:
        print("EXPLANATION ERROR:", e)
        return "حدث خطأ تقني أثناء إنشاء الشرح."


# ===============================
# Generate Terms (مصطلحات فقط)
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

Rules:
- List only the terms.
- No explanations.
- No definitions.
- No Markdown.
- Maximum 50 terms.
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
