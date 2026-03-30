import fitz
import urllib.request
import json
import os

from config import TOKEN

# 🤖 موديل أخف
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# عربي
import arabic_reshaper
from bidi.algorithm import get_display


# =========================
# تحميل الموديل (أخف 🔥)
# =========================

model_name = "Helsinki-NLP/opus-mt-en-ar"

print("Loading translation model...")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

print("Model loaded ✅")


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
# ترجمة (محسنة 🔥)
# =========================

def translate_text(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512   # 🔥 مهم جداً
    )

    outputs = model.generate(
        **inputs,
        max_length=512
    )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)


# تقسيم أصغر = أسرع
def split_text(text, size=100):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


def translate_long(text):
    chunks = split_text(text)
    results = []

    for i, c in enumerate(chunks):
        print(f"Translating chunk {i+1}/{len(chunks)}")
        results.append(translate_text(c))

    return "\n".join(results)


# =========================
# عربي PDF
# =========================

def prepare_ar(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


# =========================
# الترجمة مع تتبع 🔥
# =========================

def translate_pdf(input_pdf):

    print("Opening PDF...")
    doc = fitz.open(input_pdf)

    for page_index, page in enumerate(doc):

        print(f"Processing page {page_index + 1}")

        # 🔥 مؤقتاً حد الصفحات (اختياري للتجربة)
        # if page_index > 5:
        #     break

        blocks = page.get_text("blocks")

        for block_index, block in enumerate(blocks):

            x0, y0, x1, y1, text, *_ = block

            if not text.strip():
                continue

            try:
                translated = translate_long(text)
                translated = prepare_ar(translated)
            except Exception as e:
                print("Block Error:", e)
                continue

            rect = fitz.Rect(x0, y0, x1, y1)

            # مسح النص القديم
            page.draw_rect(rect, color=(1,1,1), fill=(1,1,1))

            # كتابة العربي
            page.insert_textbox(
                rect,
                translated,
                fontsize=10,
                align=2
            )

    output = input_pdf.replace(".pdf", "_translated.pdf")

    print("Saving translated PDF...")
    doc.save(output)
    doc.close()

    print("Done ✅")

    return output
