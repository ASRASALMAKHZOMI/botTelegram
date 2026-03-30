import fitz
import urllib.request
import json
import os
import gc
import io
import re
import time
import uuid
import arabic_reshaper
from bidi.algorithm import get_display
import torch

from config import TOKEN
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


# =========================
# ⚙️ تحميل الموديل
# =========================

model_name = "Helsinki-NLP/opus-mt-en-ar"

print("🔄 Loading translation model...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"✅ Model loaded on {device}")


# =========================
# 📂 المسارات
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "Amiri-Regular.ttf")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

if not os.path.exists(FONT_PATH):
    raise Exception("❌ ملف الخط غير موجود")


# =========================
# 📥 تحميل الملف
# =========================

def download_file(file_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode("utf-8"))

    file_path = data["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    # اسم ملف فريد
    unique_name = f"{uuid.uuid4().hex}.pdf"
    local_path = os.path.join(DOWNLOADS_DIR, unique_name)

    urllib.request.urlretrieve(download_url, local_path)
    
    # ✅ طباعة المسار فقط (وليس المحتوى)
    print(f"[DOWNLOAD] File saved to: {local_path}")
    return local_path


# =========================
# 🔍 التحقق من الملف
# =========================

def is_pdf(file_path):
    return file_path.lower().endswith(".pdf")


def is_scanned(file_path):
    try:
        doc = fitz.open(file_path)
        for page in doc:
            if page.get_text().strip():
                doc.close()
                return False
        doc.close()
        return True
    except:
        return True


# =========================
# 🌐 الترجمة
# =========================

def translate_text(text):
    if not text or not text.strip():
        return ""
    
    try:
        inputs = tokenizer(
            text.strip(),
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=512,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=2,
                do_sample=False
            )
        
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    
    except Exception as e:
        print(f"[ERROR] Translation failed: {e}")
        return text


def split_text_smart(text, max_chars=400):
    if len(text) <= max_chars:
        return [text]
    
    sentences = re.split(r'(?<=[.!?;:])\s+', text.strip())
    chunks, current_chunk = [], ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if len(sentence) > max_chars:
            words = sentence.split()
            temp_chunk = ""
            for word in words:
                if len(temp_chunk) + len(word) + 1 <= max_chars:
                    temp_chunk += " " + word
                else:
                    if temp_chunk:
                        chunks.append(temp_chunk.strip())
                    temp_chunk = word
            if temp_chunk:
                chunks.append(temp_chunk.strip())
        elif len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += " " + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]


def translate_long(text):
    if not text or len(text.strip()) < 2:
        return text
    
    chunks = split_text_smart(text.strip(), max_chars=400)
    results = []
    
    for i, c in enumerate(chunks):
        print(f"  🔄 Translating chunk {i+1}/{len(chunks)}")
        results.append(translate_text(c))
    
    return " ".join(results)


# =========================
# ✍️ تنسيق العربية
# =========================

def format_arabic_text(text):
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except:
        return text


def estimate_arabic_text_width(text, font_size):
    clean_text = re.sub(r'[\u064B-\u065B\u200B-\u200D]', '', text)
    avg_char_width = font_size * 0.6
    return len(clean_text) * avg_char_width


# =========================
# 📄 ترجمة PDF (نظيف - بدون طباعة Bytes)
# =========================

def translate_pdf(input_pdf):
    print(f"📄 Opening PDF: {os.path.basename(input_pdf)}")
    
    # مسار الملف الناتج
    base_name = os.path.splitext(input_pdf)[0]
    output_pdf = f"{base_name}_translated.pdf"
    
    doc = fitz.open(input_pdf)

    for page_index, page in enumerate(doc):
        print(f"  📑 Processing page {page_index + 1}/{len(doc)}")
        blocks = page.get_text("blocks")

        for block in blocks:
            if len(block) < 6:
                continue
                
            x0, y0, x1, y1, text, block_no, block_type = block[:7]
            
            if block_type != 0 or not text or not text.strip():
                continue
            
            clean_text = " ".join([line.strip() for line in text.split("\n") if line.strip()])
            if len(clean_text) < 2:
                continue

            try:
                translated = translate_long(clean_text)
                if not translated:
                    continue

                formatted_text = format_arabic_text(translated)

                # إخفاء النص الأصلي
                page.draw_rect(
                    fitz.Rect(x0, y0 - 2, x1, y1 + 5),
                    color=(1, 1, 1),
                    fill=(1, 1, 1),
                    width=0.1
                )

                # كتابة النص المترجم
                font_size = 10
                text_width = estimate_arabic_text_width(formatted_text, font_size)
                start_x = x1 - text_width - 3
                start_y = y0 + font_size

                page.insert_text(
                    (start_x, start_y),
                    formatted_text,
                    fontsize=font_size,
                    fontfile=FONT_PATH,
                    color=(0, 0, 0)
                )

            except Exception as e:
                print(f"    ⚠️ Error: {e}")
                continue

    # ✅ حفظ الملف (وليس tobytes)
    print(f"💾 Saving to: {os.path.basename(output_pdf)}")
    doc.save(output_pdf)
    doc.close()
    
    # التحقق من الحفظ
    if not os.path.exists(output_pdf):
        raise Exception(f"❌ الملف لم يُحفظ: {output_pdf}")
    
    file_size = os.path.getsize(output_pdf)
    print(f"✅ Saved successfully ({file_size} bytes)")
    
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ✅ إرجاع المسار فقط (وليس البيانات)
    return output_pdf


# =========================
# 🚀 المعالجة والإرسال
# =========================

def process_and_send(bot, chat_id, file_id):
    print(f"\n{'='*50}")
    print(f"🎬 New task for chat_id: {chat_id}")
    print(f"{'='*50}")
    
    try:
        bot.send_message(chat_id, "⏳ جاري معالجة الملف، يرجى الانتظار...")
    except:
        pass

    original_path = None
    translated_path = None
    
    try:
        # 1. تحميل
        original_path = download_file(file_id)

        if not is_pdf(original_path):
            bot.send_message(chat_id, "❌ الملف ليس PDF")
            return

        if is_scanned(original_path):
            bot.send_message(chat_id, "❌ هذا PDF عبارة عن صور")
            return

        # 2. ترجمة
        print("🔄 Starting translation...")
        translated_path = translate_pdf(original_path)

        # 3. تحقق قبل الإرسال
        if not os.path.exists(translated_path):
            raise Exception(f"الملف المترجم غير موجود")
        
        time.sleep(0.5)

        # 4. إرسال
        print("📤 Sending file to Telegram...")
        with open(translated_path, 'rb') as pdf_file:
            bot.send_document(
                chat_id, 
                document=pdf_file, 
                caption="✨ تمت الترجمة بنجاح!", 
                force_document=True
            )

        print("✅ File sent successfully\n")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, f"❌ حدث خطأ: {str(e)[:200]}")
        
    finally:
        # 5. تنظيف
        print("🧹 Cleaning up...")
        
        for path in [original_path, translated_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"  🗑️ Deleted: {os.path.basename(path)}")
                except:
                    pass
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        print("✅ Cleanup completed\n")


# =========================
# 🧪 اختبار
# =========================

if __name__ == "__main__":
    test_text = "Artificial intelligence is transforming the world."
    result = translate_text(test_text)
    print(f"🧪 Test: {test_text}")
    print(f"✅ Result: {result}")
