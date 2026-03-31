import fitz
import os
import urllib.request
import json
import time

from config import TOKEN
from ai_service import call_ai


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
# تنظيف النص
# =========================
def clean_text(text):

    lines = text.split("\n")
    cleaned = []
    seen = set()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line in seen:
            continue
        seen.add(line)

        line = (
            line.replace("", "-")
            .replace("", "-")
            .replace("•", "-")
            .replace("▶", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("ﬁ", "fi")
            .replace("ﬂ", "fl")
        )

        if "????" in line:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# تقسيم الصفحات إلى batches (نسخة محسنة بدون تخريب)
# =========================
def split_pages_into_batches(doc, batch_size=4):

    pages = []

    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append((i + 1, text))

    total = len(pages)
    batches = []

    i = 0

    while i < total:
        remaining = total - i

        # 🔥 تقسيم ذكي لو المتبقي قليل
        if remaining < batch_size:
            half = remaining // 2

            if half == 0:
                batches.append(pages[i:])
            else:
                batches.append(pages[i:i + half])
                batches.append(pages[i + half:i + remaining])

            break

        batch = pages[i:i + batch_size]
        batches.append(batch)
        i += batch_size

    return batches


# =========================
# ترجمة batch (عدة صفحات)
# =========================
def translate_batch(pages):

    combined_text = ""

    for page_num, text in pages:
        combined_text += f"\n📄 الصفحة {page_num}\n{text}\n"

    combined_text = clean_text(combined_text)

    prompt = f"""
أنت مترجم محترف متخصص في علوم الحاسوب.

مهمتك ترجمة النص التالي إلى العربية بدقة عالية مع الحفاظ على التنسيق.

━━━━━━━━━━━━━━━━━━━━━━
⚠️ تعليمات صارمة:
━━━━━━━━━━━━━━━━━━━━━━
- كل سطر إنجليزي وتحته ترجمته العربية مباشرة
- لا تكرر أي سطر نهائيًا حتى لو كان مختلف قليلًا
- إذا تكرر نفس السطر أو الكود، اكتب نسخة واحدة فقط
- لا تدمج الأسطر مع بعضها
- لا تضف أي شرح أو تعليق
- لا تحذف أي محتوى مهم

━━━━━━━━━━━━━━━━━━━━━━
⚠️ التعامل مع الأكواد (مهم جدًا):
━━━━━━━━━━━━━━━━━━━━━━
- أي سطر يحتوي على كود لا يتم ترجمته
- اترك الكود كما هو 100% بدون أي تعديل
- لا تغيّر ترتيب الكود أو رموزه
- لا تضف ترجمة للكود
- لا تكرر نفس الكود حتى لو كان مكتوب بصيغة مختلفة

📌 يعتبر كود إذا احتوى على:
- علامات مثل: < > / = {{ }} [ ] ( )
- أو كلمات برمجية مثل: class, id, function, return, var, const, def, import
- أو أي سطر يشبه أوامر برمجية

━━━━━━━━━━━━━━━━━━━━━━
⚠️ التنسيق:
━━━━━━━━━━━━━━━━━━━━━━
- حافظ على "📄 الصفحة X" كما هو
- لا تغير ترتيب الأسطر
- لا تكتب أي شيء خارج الترجمة

━━━━━━━━━━━━━━━━━━━━━━
⚠️ الجودة:
━━━━━━━━━━━━━━━━━━━━━━
- استخدم مصطلحات برمجية دقيقة
- اجعل الترجمة واضحة ومفهومة

━━━━━━━━━━━━━━━━━━━━━━
النص:
━━━━━━━━━━━━━━━━━━━━━━
{combined_text}
"""

    messages = [
        {"role": "system", "content": "مترجم تقني دقيق."},
        {"role": "user", "content": prompt}
    ]

    attempt = 0

    while True:
        try:
            result = call_ai(
    messages,
    model="llama-3.1-8b-instant",
    temperature=0.3,
    max_tokens=500
)

            if result and result.strip():
                time.sleep(2)
                return result

        except Exception as e:
            print(f"[BATCH ERROR {attempt}]:", e)

        wait = min(10, 2 + attempt)
        time.sleep(wait)

        attempt += 1

        # 🔥 fallback بعد 5 محاولات
        if attempt >= 5:
            return None
