import fitz
import urllib.request
import json
import os
import gc
import io
import arabic_reshaper
from bidi.algorithm import get_display

from config import TOKEN
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


# =========================
# تحميل الموديل
# =========================

model_name = "Helsinki-NLP/opus-mt-en-ar"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
print("Model loaded ✅")


# =========================
# المسارات
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "Amiri-Regular.ttf")

if not os.path.exists(FONT_PATH):
    raise Exception("❌ الخط غير موجود")


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
# التحقق من PDF
# =========================

def is_pdf(file_path):
    return file_path.lower().endswith(".pdf")


def is_scanned(file_path):
    doc = fitz.open(file_path)
    for page in doc:
        if page.get_text().strip():
            doc.close()
            return False
    doc.close()
    return True


# =========================
# الترجمة
# =========================

def translate_text(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    outputs = model.generate(**inputs, max_length=512)

    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def split_text(text, size=50):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


def translate_long(text):

    chunks = split_text(text)
    results = []

    for i, c in enumerate(chunks):
        print(f"[AI] Chunk {i+1}/{len(chunks)}")
        results.append(translate_text(c))

    return " ".join(results)


# =========================
# الترجمة داخل PDF
# =========================

def translate_pdf(input_pdf):

    print("[PDF] Opening...")
    doc = fitz.open(input_pdf)

    for page_index, page in enumerate(doc):

        print(f"[PAGE] {page_index + 1}")

        blocks = page.get_text("blocks")

        for block_index, block in enumerate(blocks):

            x0, y0, x1, y1, text, *_ = block

            if not text.strip():
                continue

            lines = text.split("\n")
            current_y = y0

            for line in lines:

                if not line.strip():
                    continue

                try:
                    translated = translate_long(line)

                    # ✅ إصلاح العربية
                    reshaped = arabic_reshaper.reshape(translated)
                    bidi_text = get_display(reshaped)

                except Exception as e:
                    print("[ERROR]", e)
                    continue

                # ✅ حساب عرض النص (محاذاة يمين)
                text_width = fitz.get_text_length(
                    bidi_text,
                    fontname="helv",
                    fontsize=10
                )

                x_position = x1 - text_width - 5

                # ✅ كتابة الترجمة
                page.insert_text(
                    (x_position, current_y + 10),
                    bidi_text,
                    fontsize=10,
                    fontfile=FONT_PATH
                )

                current_y += 20

    # =========================
    # تحويل إلى Bytes (مؤقت)
    # =========================

    pdf_bytes = doc.tobytes()

    doc.close()
    del doc
    gc.collect()

    print("[DONE] ✅ Translation ready")

    return pdf_bytes


# =========================
# إرسال + تنظيف كامل
# =========================

def process_and_send(bot, chat_id, file_id):

    print(f"[START] Task for chat_id: {chat_id}")

    file_path = download_file(file_id)

    if not is_pdf(file_path):
        bot.send_message(chat_id, "❌ الملف ليس PDF")
        return

    if is_scanned(file_path):
        bot.send_message(chat_id, "❌ هذا PDF عبارة عن صور")
        return

    print("[STEP] Starting translation...")

    pdf_data = translate_pdf(file_path)

    # 🔥 تحويل إلى ملف وهمي (مهم جدًا)
    pdf_file = io.BytesIO(pdf_data)
    pdf_file.name = "translated.pdf"

    # 🚀 إرسال
    bot.send_document(chat_id, pdf_file)

    # 🧹 تنظيف كامل
    pdf_file.close()
    del pdf_file
    del pdf_data
    gc.collect()

    try:
        os.remove(file_path)
    except:
        pass

    print("[END TASK] 🧹 Cleaned بالكامل")
