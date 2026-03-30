import fitz
import urllib.request
import json
import os

from config import TOKEN

# 🤖 موديل خفيف وسريع
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# عربي
import arabic_reshaper
from bidi.algorithm import get_display


# =========================
# تحميل الموديل
# =========================

model_name = "Helsinki-NLP/opus-mt-en-ar"

print("[MODEL] Loading...")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

print("[MODEL] Loaded ✅")


# =========================
# تحميل ملف من تيليجرام
# =========================

def download_file(file_id):

    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode("utf-8"))

    file_path = data["result"]["file_path"]

    download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    os.makedirs("downloads", exist_ok=True)

    local_path = "downloads/" + os.path.basename(file_path)

    urllib.request.urlretrieve(download_url, local_path)

    return local_path


# =========================
# تحقق PDF
# =========================

def is_pdf(file_path):
    return file_path.lower().endswith(".pdf")


def is_scanned(file_path):
    doc = fitz.open(file_path)

    for page in doc:
        if page.get_text().strip():
            return False

    return True


# =========================
# ترجمة النص
# =========================

def translate_text(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    outputs = model.generate(
        **inputs,
        max_length=512
    )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def split_text(text, size=100):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


def translate_long(text):
    chunks = split_text(text)
    results = []

    for i, c in enumerate(chunks):
        print(f"[TRANSLATE] chunk {i+1}/{len(chunks)}")
        results.append(translate_text(c))

    return "\n".join(results)


# =========================
# تجهيز العربي
# =========================

def prepare_ar(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


# =========================
# ترجمة PDF (احترافي 🔥)
# =========================

def translate_pdf(input_pdf):

    font_path = "Amiri-Regular.ttf"  # 🔥 لازم تضيف الخط

    print("[PDF] Opening file...")
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()

    for page_index, page in enumerate(doc):

        print(f"[PDF] Processing page {page_index + 1}")

        new_page = new_doc.new_page(
            width=page.rect.width,
            height=page.rect.height
        )

        blocks = page.get_text("blocks")

        for block in blocks:

            x0, y0, x1, y1, text, *_ = block

            if not text.strip():
                continue

            try:
                translated = translate_long(text)
                translated = prepare_ar(translated)

            except Exception as e:
                print("[ERROR] Block:", e)
                continue

            rect = fitz.Rect(x0, y0, x1, y1)

            # =========================
            # الإنجليزي (فوق)
            # =========================
            new_page.insert_textbox(
                rect,
                text,
                fontsize=10,
                fontname="helv",
                align=0  # يسار
            )

            # =========================
            # العربي (تحت)
            # =========================
            new_rect = fitz.Rect(x0, y0 + 15, x1, y1 + 15)

            new_page.insert_textbox(
                new_rect,
                translated,
                fontsize=10,
                fontfile=font_path,
                align=2  # يمين
            )

    output = input_pdf.replace(".pdf", "_translated.pdf")

    print("[PDF] Saving translated file...")
    new_doc.save(output)
    new_doc.close()
    doc.close()

    print("[DONE] Translation finished ✅")

    return output
