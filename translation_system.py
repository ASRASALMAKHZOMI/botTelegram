import fitz
import urllib.request
import json
import os
import gc
import io
import re
import arabic_reshaper
from bidi.algorithm import get_display
import torch

from config import TOKEN
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


# =========================
# ⚙️ تحميل الموديل والإعدادات
# =========================

model_name = "Helsinki-NLP/opus-mt-en-ar"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# نقل الموديل للـ GPU إذا متاح لتسريع الترجمة
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Model loaded ✅ on {device}")


# =========================
# 📂 المسارات
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "Amiri-Regular.ttf")

if not os.path.exists(FONT_PATH):
    raise Exception("❌ الخط غير موجود")


# =========================
# 📥 تحميل ملف من تيليجرام
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
# 🔍 التحقق من PDF
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
# 🌐 الترجمة (محسّنة)
# =========================

def translate_text(text):
    """ترجمة نص باستخدام الموديل مع معايير جودة عالية"""
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
        
        # نقل المدخلات لنفس جهاز الموديل (CPU/GPU)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=512,
                num_beams=4,              # ✅ دقة أعلى
                early_stopping=True,      # ✅ كفاءة أعلى
                no_repeat_ngram_size=2,   # ✅ منع التكرار
                do_sample=False           # ✅ نتائج متسقة
            )
        
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    
    except Exception as e:
        print(f"[ERROR] Translation failed: {e}")
        return text


def split_text_smart(text, max_chars=400):
    """تقسيم النص عند علامات الترقيم للحفاظ على المعنى"""
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
    """ترجمة النصوص الطويلة بتقسيمها ذكياً"""
    if not text or len(text.strip()) < 2:
        return text
    
    chunks = split_text_smart(text.strip(), max_chars=400)
    results = []
    
    for i, c in enumerate(chunks):
        print(f"[AI] Chunk {i+1}/{len(chunks)}")
        results.append(translate_text(c))
    
    return " ".join(results)


# =========================
# ✍️ تنسيق العربية
# =========================

def format_arabic_text(text):
    """تنسيق النص العربي للعرض الصحيح (RTL + تشكيل)"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except:
        return text


def estimate_arabic_text_width(text, font_size):
    """تقدير عرض النص العربي لأن الخطوط المخصصة لا تُقاس بدقة تلقائية"""
    clean_text = re.sub(r'[\u064B-\u065B\u200B-\u200D]', '', text)
    avg_char_width = font_size * 0.6
    return len(clean_text) * avg_char_width


# =========================
# 📄 الترجمة داخل PDF (محسّنة)
# =========================

def translate_pdf(input_pdf):
    print("[PDF] Opening...")
    doc = fitz.open(input_pdf)

    for page_index, page in enumerate(doc):
        print(f"[PAGE] {page_index + 1}")
        blocks = page.get_text("blocks")

        for block in blocks:
            if len(block) < 6:
                continue
                
            x0, y0, x1, y1, text, block_no, block_type = block[:7]
            
            # تخطي الكتل غير النصية
            if block_type != 0 or not text or not text.strip():
                continue
            
            # تنظيف النص
            clean_text = " ".join([line.strip() for line in text.split("\n") if line.strip()])
            if len(clean_text) < 2:
                continue

            try:
                # ✅ ترجمة النص
                translated = translate_long(clean_text)
                if not translated:
                    continue

                # ✅ تنسيق العربية
                formatted_text = format_arabic_text(translated)

                # ✅ إخفاء النص الأصلي (رسم مستطيل أبيض فوقه)
                page.draw_rect(
                    fitz.Rect(x0, y0 - 2, x1, y1 + 5),
                    color=(1, 1, 1),
                    fill=(1, 1, 1),
                    width=0.1
                )

                # ✅ حساب الموضع والكتابة
                font_size = 10
                text_width = estimate_arabic_text_width(formatted_text, font_size)
                start_x = x1 - text_width - 3  # محاذاة لليمين
                start_y = y0 + font_size

                page.insert_text(
                    (start_x, start_y),
                    formatted_text,
                    fontsize=font_size,
                    fontfile=FONT_PATH,
                    color=(0, 0, 0)
                )

            except Exception as e:
                print("[ERROR]", e)
                continue

    pdf_bytes = doc.tobytes()
    doc.close()
    gc.collect()
    
    # تنظيف ذاكرة GPU إذا وجدت
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print("[DONE] ✅ Translation ready")
    return pdf_bytes


# =========================
# 🚀 إرسال + تنظيف كامل
# =========================

def process_and_send(bot, chat_id, file_id):
    print(f"[START] Task for chat_id: {chat_id}")
    
    # إرسال رسالة انتظار
    try:
        bot.send_message(chat_id, "⏳ جاري معالجة الملف، يرجى الانتظار...")
    except:
        pass

    file_path = None
    try:
        file_path = download_file(file_id)

        if not is_pdf(file_path):
            bot.send_message(chat_id, "❌ الملف ليس PDF")
            return

        if is_scanned(file_path):
            bot.send_message(chat_id, "❌ هذا PDF عبارة عن صور")
            return

        print("[STEP] Starting translation...")
        pdf_data = translate_pdf(file_path)

        pdf_file = io.BytesIO(pdf_data)
        pdf_file.name = "translated.pdf"

        bot.send_document(chat_id, pdf_file, caption="✨ تمت الترجمة بنجاح!")

        pdf_file.close()
        print("[END TASK] 🧹 Cleaned بالكامل")
        
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ: {str(e)[:200]}")
        
    finally:
        # تنظيف الملفات المؤقتة
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        if 'pdf_data' in locals():
            del pdf_data
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# =========================
# 🧪 اختبار محلي (اختياري)
# =========================

if __name__ == "__main__":
    test_text = "Artificial intelligence is transforming the world."
    result = translate_text(test_text)
    print(f"🧪 Test: {test_text}")
    print(f"✅ Result: {result}")
