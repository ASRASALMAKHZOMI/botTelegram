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
# Prompts ثابتة لدعم الكاشينق
# ==============================

CHALLENGE_SYSTEM_PROMPT = """
أنت مدرس برمجة يشرح لطلاب مبتدئين.

اكتب المسائل بأسلوب بسيط جدًا مهما كان المستوى.
استخدم جمل قصيرة.
لا تستخدم أسلوب أكاديمي.
لا تستخدم كلمات معقدة.
اشرح المطلوب مباشرة.
حتى لو كانت الفكرة صعبة، يجب أن تكون القراءة سهلة جدًا.
"""

# ---------- سهل ----------

EASY_PROMPT = """
أنشئ سؤال خوارزمي بسيط.

اكتب فقط بالصيغة التالية:

عنوان:

المسألة:

Input:
(وضح شكل الإدخال فقط)

Output:
(وضح المطلوب فقط)

Test Cases:

Test 1:
Input:
...
Output:
...

Test 2:
Input:
...
Output:
...

Test 3:
Input:
...
Output:
...

لا تكتب الحل.
"""

# ---------- متوسط ----------

MEDIUM_PROMPT = """
أنشئ مشروعًا مصغرًا بسيطًا مثل:
- حساب ضريبة
- نظام خصومات
- حساب درجات
- فاتورة شراء
- حساب عمولة

يجب أن يحتوي على عدة شروط واضحة.

اكتب فقط بالصيغة التالية:

عنوان:

المسألة:

Input:
(وضح شكل الإدخال فقط)

Output:
(وضح المطلوب فقط)

Test Cases:

Test 1:
Input:
...
Output:
...

Test 2:
Input:
...
Output:
...

Test 3:
Input:
...
Output:
...

لا تكتب الحل.
"""

# ---------- صعب ----------

HARD_PROMPT = """
أنشئ متطلبات مشروع برمجي.

يجب أن يكون على شكل نظام كامل.
اكتب المتطلبات كنقاط واضحة.
لا تكتب حالات اختبار.

اكتب فقط بالصيغة التالية:

عنوان:

المسألة:

Input:
(وضح شكل الإدخال العام)

Output:
(وضح النتائج المتوقعة بشكل عام)

لا تكتب الحل.
"""

VALIDATION_SYSTEM_PROMPT = """
أجب فقط بكلمة واحدة:
واضح
أو
غير_واضح
"""

EVALUATION_SYSTEM_PROMPT = """
أنت مراجع أكواد برمجية محترف لأي لغة برمجة.

عند الرد التزم بالهيكل التالي:

التقييم من 10:

مستوى الحل:

تحليل المنطق:

الأخطاء والملاحظات:

إذا لم توجد أخطاء اكتب:
لا توجد أخطاء مؤكدة ضمن حدود الكود المعروض.

التحسينات:

إذا لم توجد تحسينات اكتب:
لا توجد تحسينات جوهرية مثبتة تقنيًا في حدود الكود المعروض.

اكتب الرد كنص عادي فقط.
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
# الاتصال بالذكاء
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

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        return clean_text(content)

    except Exception as e:
        print("AI ERROR:", e)
        return "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي."

# ==============================
# توليد تحدي
# ==============================

def generate_challenge(level):

    if level == "سهل":
        prompt = EASY_PROMPT
        required_sections = ["Test 1:", "Test 2:", "Test 3:"]

    elif level == "متوسط":
        prompt = MEDIUM_PROMPT
        required_sections = ["Test 1:", "Test 2:", "Test 3:"]

    else:
        prompt = HARD_PROMPT
        required_sections = []

    messages = [
        {"role": "system", "content": CHALLENGE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    for _ in range(3):
        challenge = call_ai(messages, temperature=0.3, max_tokens=1200)

        if "عنوان:" in challenge and "المسألة:" in challenge:
            if all(section in challenge for section in required_sections):
                return challenge
            if not required_sections:
                return challenge

    return "تعذر إنشاء مسألة مكتملة. حاول مرة أخرى."

# ==============================
# التحقق من وضوح التحدي
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

    return call_ai(messages, temperature=0.2, max_tokens=1000)

# ==============================
# نظام التحديات
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
