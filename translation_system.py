import fitz
import urllib.request
import json
import os
import gc
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

    unique_name = f"{uuid.uuid4().hex}.pdf"
    local_path = os.path.join(DOWNLOADS_DIR, unique_name)

    urllib.request.urlretrieve(download_url, local_path)
    print(f"[DOWNLOAD] Saved: {local_path}")
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
# 🧹 تنظيف النص (حاسم جداً!)
# =========================

def clean_extracted_text(text):
    """إزالة كل الرموز الغريبة التي تمنع الترجمة"""
    if not text:
        return ""
    
    # إزالة رموز التحكم غير المرئية
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    # إزالة الرموز النقطية الغريبة
    text = re.sub(r'[·•◦‣⁃∙●○◘◙●■□▪▫]', ' ', text)
    
    # إزالة الرموز الخاصة
    text = re.sub(r'[]', '', text)
    
    # إزالة الرموز غير المفيدة
    text = re.sub(r'[^\w\s.,!?;:\'\"()\[\]{}-]', ' ', text)
    
    # توحيد المسافات
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# =========================
# 🌐 الترجمة
# =========================

def translate_text(text):
    if not text or len(text.strip()) < 3:
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
        
        result = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        
        if not result or result == text.strip():
            return ""
        
        return result
    
    except Exception as e:
        print(f"[ERROR] Translation: {e}")
        return ""


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
    if not text or len(text.strip()) < 3:
        return ""
    
    chunks = split_text_smart(text.strip(), max_chars=400)
    results = []
    
    for i, c in enumerate(chunks):
        cleaned = clean_extracted_text(c)
        if cleaned:
            print(f"  🔄 Chunk {i+1}/{len(chunks)}: {cleaned[:50]}...")
            translated = translate_text(cleaned)
            if translated:
                results.append(translated)
    
    return " ".join(results) if results else ""


# =========================
# ✍️ تنسيق العربية (الحل الجذري)
# =========================

def format_arabic_text(text):
    """تنسيق النص العربي مع دعم RTL الصحيح"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except:
        return text


# =========================
# 📄 ترجمة PDF (مُعدّلة للحل الأفقي)
# =========================

def translate_pdf(input_pdf):
    print(f"📄 Opening: {os.path.basename(input_pdf)}")
    
    base_name = os.path.splitext(input_pdf)[0]
    output_pdf = f"{base_name}_translated.pdf"
    
    doc = fitz.open(input_pdf)
    total_pages = len(doc)
    
    for page_index, page in enumerate(doc):
        print(f"  📑 Page {page_index + 1}/{total_pages}")
        
        # استخراج النص بطريقة dict
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_text = span.get("text", "").strip()
                    if span_text:
                        block_text += span_text + " "
            
            cleaned_text = clean_extracted_text(block_text)
            
            if not cleaned_text or len(cleaned_text) < 5:
                continue
            
            print(f"    📝 Found: {cleaned_text[:60]}...")
            
            try:
                translated = translate_long(cleaned_text)
                
                if not translated:
                    print(f"    ⚠️ No translation")
                    continue
                
                formatted_text = format_arabic_text(translated)
                
                if not formatted_text:
                    continue
                
                print(f"    ✅ Translated: {formatted_text[:60]}...")
                
                # إحداثيات الكتلة
                x0 = block.get("bbox", [0, 0, 0, 0])[0]
                y0 = block.get("bbox", [0, 0, 0, 0])[1]
                x1 = block.get("bbox", [0, 0, 0, 0])[2]
                y1 = block.get("bbox", [0, 0, 0, 0])[3]
                
                # ✅ إخفاء النص الأصلي
                page.draw_rect(
                    fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2),
                    color=(1, 1, 1),
                    fill=(1, 1, 1),
                    width=0
                )
                
                # ✅ الحل الجذري: استخدام insert_textbox بدلاً من insert_text
                # هذا يضمن كتابة النص أفقياً من اليمين لليسار
                rect = fitz.Rect(x0, y0, x1, y1 + 20)
                
                page.insert_textbox(
                    rect,
                    formatted_text,
                    fontsize=10,
                    fontfile=FONT_PATH,
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_RIGHT,  # ✅ محاذاة لليمين للعربي
                    rotate=0,  # ✅ بدون تدوير (أفقي)
                    render_mode=0
                )
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # حفظ
    print(f"💾 Saving: {os.path.basename(output_pdf)}")
    doc.save(output_pdf)
    doc.close()
    
    if not os.path.exists(output_pdf):
        raise Exception(f"❌ File not saved: {output_pdf}")
    
    file_size = os.path.getsize(output_pdf)
    print(f"✅ Saved ({file_size} bytes)")
    
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return output_pdf


# =========================
# 🚀 المعالجة والإرسال
# =========================

def process_and_send(bot, chat_id, file_id):
    print(f"\n{'='*50}")
    print(f"🎬 Task for chat_id: {chat_id}")
    print(f"{'='*50}")
    
    try:
        bot.send_message(chat_id, "⏳ جاري المعالجة...")
    except:
        pass

    original_path = None
    translated_path = None
    
    try:
        original_path = download_file(file_id)

        if not is_pdf(original_path):
            bot.send_message(chat_id, "❌ ليس PDF")
            return

        if is_scanned(original_path):
            bot.send_message(chat_id, "❌ ملف صور (ممسوح)")
            return

        print("🔄 Translating...")
        translated_path = translate_pdf(original_path)

        if not os.path.exists(translated_path):
            raise Exception("الملف المترجم غير موجود")
        
        time.sleep(0.5)

        print("📤 Sending...")
        with open(translated_path, 'rb') as pdf_file:
            bot.send_document(
                chat_id, 
                document=pdf_file, 
                caption="✨ تمت الترجمة!",
                force_document=True
            )

        print("✅ Sent\n")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, f"❌ خطأ: {str(e)[:200]}")
        
    finally:
        print("🧹 Cleaning...")
        
        for path in [original_path, translated_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"  🗑️ {os.path.basename(path)}")
                except:
                    pass
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        print("✅ Done\n")


# =========================
# 🧪 اختبار
# =========================

if __name__ == "__main__":
    test = "Arrays are collections of variables."
    result = translate_text(test)
    print(f"🧪 {test}")
    print(f"✅ {result}")
