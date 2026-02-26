import os
import requests

import re

def clean_text(text):
    # إزالة النجوم الخاصة بالـ Markdown
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # إزالة علامات القوائم
    text = text.replace("- ", "• ")

    return text

# ==============================
# إعدادات
# ==============================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"

user_states = {}  # حفظ حالة المستخدم مؤقتًا


# ==============================
# دالة الاتصال بالذكاء
# ==============================

def call_ai(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.7
    }

    response = requests.post(URL, headers=headers, json=data, timeout=20)
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]

    return clean_text(content)


# ==============================
# توليد تحدي
# ==============================

def generate_challenge(level):
    prompt = f"""
    أنشئ تحدي برمجي مستوى {level}.
    لا تكتب الحل.
    اكتب فقط:
    - عنوان
    - وصف
    - مثال إدخال وإخراج
    """

    messages = [
        {"role": "system", "content": "أنت خبير في إنشاء تحديات برمجية."},
        {"role": "user", "content": prompt}
    ]

    return call_ai(messages)


# ==============================
# تقييم الكود
# ==============================

def evaluate_code(challenge, code):
    messages = [
        {
            "role": "system",
            "content": """أنت مراجع أكواد برمجية محترف لأي لغة برمجة.
مهمتك تحليل الكود المُرسل لك اعتمادًا على ما هو موجود فيه حرفيًا فقط.

عند الرد، التزم بالهيكل التالي دون إضافة أقسام أخرى:

التقييم من 10:
أعطِ تقييمًا مدعومًا بسبب تقني مباشر مستند إلى الكود نفسه.
لا تقيّم الفكرة العامة للمسألة، بل قيّم التنفيذ التقني فقط.

تحليل المنطق:
صف ما يفعله الكود خطوة بخطوة بدقة.
اربط كل خطوة بالجزء النصي الدال عليها في الكود (مثل: "داخل الدالة main"، "في الحلقة for"، "في شرط if") دون افتراض أرقام أسطر.

الأخطاء والملاحظات:
اذكر فقط الأخطاء أو المشكلات التي يمكن إثباتها من الكود نفسه.
كل ملاحظة يجب أن تكون مدعومة بسبب تقني واضح ومحدد، مع الإشارة إلى الجزء الذي استندت إليه.
إذا لم توجد أخطاء مؤكدة، اذكر ذلك صراحة.
لا تفترض متطلبات غير مذكورة.

التحسينات:
اقترح فقط تحسينات لها أثر تقني حقيقي.
كل تحسين يجب أن يكون مبرّرًا بوضوح:
- ما المشكلة الحالية؟
- لماذا هذا الاقتراح أفضل؟
- ما أثره الفعلي على الأداء أو الوضوح أو الأمان؟

قيود صارمة:

- لا تفترض سلوكًا أو متطلبات غير مذكورة.
- لا تنسب للكود خصائص غير موجودة.
- لا تختلق أخطاء أو مشاكل غير قابلة للاستنتاج من الكود.
- لا تقدّم تحسينات شكلية بلا أثر تقني حقيقي.
- إذا كان السياق غير كافٍ للحكم على نقطة معيّنة، صرّح بذلك بوضوح.
- لا تستخدم عبارات عامة أو مبهمة؛ كل حكم تقني يجب أن يكون مفسّرًا ومعلَّلًا.

اكتب الرد كنص عادي بدون Markdown أو تعداد أو رموز خاصة.
لا تذكر أي تعليمات أو قواعد في الرد."""
        },
        {
            "role": "user",
            "content": f"""
هذا هو التحدي:
{challenge}

هذا هو كود المستخدم:
{code}

اكتب الرد بالتنسيق التالي فقط:

التقييم من 10: X/10

تحليل المنطق:
(فقرة واحدة)

الأخطاء والملاحظات:
(فقرة واحدة)

التحسينات:
(فقرة واحدة)
"""
        }
    ]

    return clean_text(call_ai(messages))


# ==============================
# مثال منطق التعامل مع الرسائل
# ==============================

def handle_message(user_id, message_text):

    # لو اختار مستوى
    if message_text in ["سهل", "متوسط", "صعب"]:
        challenge = generate_challenge(message_text)

        user_states[user_id] = {
            "challenge": challenge,
            "waiting_for_code": True
        }

        return challenge + "\n\n💻 أرسل الكود الخاص بك الآن."

    # لو أرسل كود بعد التحدي
    if user_id in user_states and user_states[user_id]["waiting_for_code"]:
        challenge = user_states[user_id]["challenge"]

        evaluation = evaluate_code(challenge, message_text)

        del user_states[user_id]  # مسح الحالة بعد التقييم

        return evaluation

    return "اختر مستوى: سهل - متوسط - صعب"

