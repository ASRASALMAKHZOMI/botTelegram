import os
import requests
import re

# ==============================
# إعدادات
# ==============================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL_NAME = "openai/gpt-oss-120b"
DEFAULT_MAX_TOKENS = 1200

user_states = {}

# ==============================
# Prompts ثابتة (Bootcamp Mode)
# ==============================

CHALLENGE_SYSTEM_PROMPT = """
أنت مدرب Bootcamp برمجة.

اكتب المسائل بأسلوب بسيط جدًا مهما كان المستوى.
استخدم جمل قصيرة.
لا تستخدم أسلوب أكاديمي.
اشرح المطلوب مباشرة.
لا تكرر نفس الفكرة في كل مرة.
يجب أن تبني كل مرحلة مهارة مختلفة.
"""

# ==============================
# 🟢 المرحلة الأولى (منطق أساسي)
# ==============================

EASY_PROMPT = """
أنشئ تمرينًا ضمن المرحلة الأولى من Bootcamp البرمجة.

المرحلة الأولى تركز على:
- المقارنات بين عناصر
- إيجاد الأكبر أو الأصغر
- ترتيب عناصر بسيطة
- التحقق من تسلسل
- عدّ تكرارات
- تحليل نص بسيط
- مقارنة حروف أو كلمات

لا تستخدم أفكارًا مكررة مثل جمع رقمين أو حساب متوسط فقط.
اختر فكرة منطقية تبني مهارة واضحة.

اكتب فقط بالصيغة التالية:

عنوان:

المسألة:

Input:
(وضح شكل الإدخال فقط)

Output:
(وضح المطلوب فقط)

لا تكتب الحل.
"""

# ==============================
# 🟡 المرحلة الثانية (خوارزمية متعددة الخطوات)
# ==============================

MEDIUM_PROMPT = """
أنشئ خوارزمية متوسطة متعددة الخطوات.

يمكن أن تتضمن:
- تحليل نص
- عدّ بشروط
- ترتيب عناصر
- تصنيف بيانات
- مقارنة عناصر
- فلترة قائمة
- تحويل بيانات
- تشفير بسيط
- حساب فرق تواريخ

لا تجعلها مشروعًا إداريًا.
لا تجعلها نظام CRUD.
لا تستخدم نفس المجال في كل مرة.
اجعلها تحتوي عدة شروط مترابطة.

اكتب فقط بالصيغة التالية:

عنوان:

المسألة:

Input:
(وضح شكل الإدخال فقط)

Output:
(وضح المطلوب فقط)

لا تكتب الحل.
"""

# ==============================
# 🔴 المرحلة الثالثة (خوارزمية مركبة)
# ==============================

HARD_PROMPT = """
أنشئ خوارزمية صعبة لكنها برمجية فقط.

الشروط:
- لا تستخدم أي قوانين رياضية أو فيزيائية.
- لا تعتمد على معادلات.
- لا تستخدم مفاهيم زمن/سرعة/مسافة.
- لا تجعلها تحليل بيانات أكاديمي.
- لا تجعلها مسألة حسابية بحتة.

يجب أن:
- تعتمد على منطق ذكي.
- تحتوي شرطًا غير مباشر.
- تحتاج تفكير عميق.
- تكون بسيطة في الوصف.
- لا تحتوي قائمة طويلة من التعليمات.

اكتب فقط:

عنوان:

المسألة:

Input:
(وضح شكل الإدخال فقط)

Output:
(وضح المطلوب فقط)

لا تكتب الحل.
"""

# ==============================
# تحقق الوضوح
# ==============================

VALIDATION_SYSTEM_PROMPT = """
أجب بكلمة واحدة فقط:
واضح
أو
غير_واضح
"""

# ==============================
# نظام التقييم الكامل (كما كان عندك)
# ==============================

EVALUATION_SYSTEM_PROMPT = """
أنت مراجع أكواد برمجية محترف لأي لغة برمجة.
مهمتك تحليل الكود المُرسل لك اعتمادًا فقط على ما هو مكتوب فيه حرفيًا.

عند الرد، التزم بالهيكل التالي دون إضافة أقسام أخرى:

التقييم من 10:
قيّم التنفيذ التقني فقط وليس الفكرة العامة.

مستوى الحل:
حدد مستوى مهارة المبرمج بناءً على جودة الحل نفسه وليس صعوبة السؤال.
التصنيفات الممكنة:
- مبتدى: تنفيذ مباشر وبسيط بدون تحسينات أو تفكير إضافي.
- جيد: حل صحيح ومنظم.
- متقدم: استخدام تقنيات غير مباشرة أو فهم عميق للمشكلة.
- احترافي: حل فعال، آمن، يراعي الحواف والقيود الكبيرة.

تحليل المنطق:
صف ما يفعله الكود خطوة بخطوة بدقة.
اربط الشرح بأجزاء واضحة من الكود مثل: داخل main، في if، في for.

الأخطاء والملاحظات:
اذكر فقط الأخطاء التي يمكن إثباتها من الكود نفسه.
إذا لم توجد أخطاء مؤكدة، اكتب حرفيًا:
لا توجد أخطاء مؤكدة ضمن حدود الكود المعروض.

التحسينات:
اقترح فقط تحسينات تقنية حقيقية.
إذا لم توجد تحسينات جوهرية مثبتة تقنيًا، اكتب حرفيًا:
لا توجد تحسينات جوهرية مثبتة تقنيًا في حدود الكود المعروض.

لا تستخدم LaTeX.
اكتب الرد كنص عادي بدون Markdown.
"""

# ==============================
# تنظيف النص
# ==============================

def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return text.strip()

# ==============================
# الاتصال بالذكاء (نفس توقيعك الأصلي)
# ==============================

def call_ai(messages, model=None, temperature=0.3, max_tokens=DEFAULT_MAX_TOKENS):

    if model is None:
        model = MODEL_NAME

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(
            URL,
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()

        return clean_text(
            response.json()["choices"][0]["message"]["content"]
        )

    except requests.exceptions.Timeout:
        return "انتهى وقت الاتصال بالذكاء الاصطناعي. حاول مرة أخرى."

    except requests.exceptions.RequestException as e:
        print("AI ERROR:", e)
        return "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي. حاول مرة أخرى."

# ==============================
# توليد التحدي
# ==============================

def generate_challenge(level):

    if level == "سهل":
        prompt = EASY_PROMPT
    elif level == "متوسط":
        prompt = MEDIUM_PROMPT
    else:
        prompt = HARD_PROMPT

    messages = [
        {"role": "system", "content": CHALLENGE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    for _ in range(3):
        challenge = call_ai(messages, temperature=0.3, max_tokens=DEFAULT_MAX_TOKENS)
        if "عنوان:" in challenge and "المسألة:" in challenge:
            return challenge

    return "تعذر إنشاء مسألة مكتملة. حاول مرة أخرى."

# ==============================
# التحقق من الوضوح
# ==============================

def validate_challenge(challenge_text):

    messages = [
        {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
        {"role": "user", "content": challenge_text}
    ]

    result = call_ai(messages, temperature=0, max_tokens=10)
    return "واضح" in result

# ==============================
# تقييم الكود
# ==============================

def evaluate_code(challenge, code):

    user_prompt = f"""
هذا هو التحدي:
{challenge}

هذا هو كود المستخدم:
{code}
"""

    messages = [
        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    return call_ai(messages, temperature=0.2, max_tokens=DEFAULT_MAX_TOKENS)

# ==============================
# إدارة الرسائل
# ==============================

def handle_message(user_id, message_text):

    clean_text_msg = message_text.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()

    if clean_text_msg in ["سهل", "متوسط", "صعب"]:

        challenge = generate_challenge(clean_text_msg)

        if validate_challenge(challenge):
            user_states[user_id] = {
                "challenge": challenge,
                "waiting_for_code": True
            }
            return challenge + "\n\n💻 أرسل الكود الخاص بك الآن."

        return "تعذر توليد تحدي واضح."

    if user_id in user_states and user_states[user_id]["waiting_for_code"]:

        challenge = user_states[user_id]["challenge"]
        evaluation = evaluate_code(challenge, message_text)

        del user_states[user_id]
        return evaluation

    return "اختر مستوى: سهل - متوسط - صعب"

