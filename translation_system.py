import fitz
from ai_service import call_ai

# =========================
# استخراج سطور
# =========================
def extract_lines(pdf_path):

    doc = fitz.open(pdf_path)
    lines = []

    for page in doc:
        text = page.get_text()
        for line in text.split("\n"):
            clean = line.strip()
            if clean:
                lines.append(clean)

    doc.close()
    return lines


# =========================
# ترجمة سطر
# =========================
def translate_line(line):

    prompt = f"""
ترجم السطر التالي إلى العربية فقط:

{line}
"""

    messages = [
        {"role": "system", "content": "مترجم دقيق."},
        {"role": "user", "content": prompt}
    ]

    result = call_ai(messages)
    return result.strip() if result else ""


# =========================
# ترجمة كامل (نص واحد)
# =========================
def translate_to_text(pdf_path):

    lines = extract_lines(pdf_path)

    output = []

    for line in lines:
        try:
            ar = translate_line(line)
            output.append(f"{line}\n{ar}\n")
        except:
            output.append(f"{line}\n[خطأ]\n")

    return "\n".join(output)
