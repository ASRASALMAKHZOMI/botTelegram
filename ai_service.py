import os
import requests
import re

# ==============================
# إعدادات Groq مباشرة
# ==============================

AI_API_KEY = os.getenv("GROQ_API_KEY")
AI_BASE_URL = "https://api.groq.com/openai/v1"
AI_MODEL = "openai/gpt-oss-120b"

# ⚡ تقليل التوكنز لتسريع الاستجابة
DEFAULT_MAX_TOKENS = 1200

user_states = {}

# ==============================
# تنظيف آمن
# ==============================

def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text.strip()

# =====================================================
# SYSTEM PROMPTS (ثابتة 100% لتفعيل Prompt Caching)
# =====================================================

EVALUATION_SYSTEM_PROMPT = """أنت مراجع أكواد برمجية احترافي. قيّم الحل تقنيًا من 10 درجات فقط بناءً على ما هو مكتوب في الكود.

أولًا حدّد مستوى التحدي (بسيط / متوسط / متقدم) اعتمادًا على وصفه.

معايير التقييم:

- بسيط:
قيّم صحة التنفيذ والوضوح فقط. لا تخصم بسبب عدم استخدام تقنيات متقدمة. لا يتم الخصم إلا عند وجود خطأ منطقي مثبت.

- متوسط:
قيّم صحة التنفيذ، تنظيم الكود، وضوح المنطق، والتعامل مع الحالات المتوقعة. يمكن الخصم عند وجود ضعف تنظيمي واضح أو إهمال حالة مهمة.

- متقدم:
قيّم جودة التصميم، الكفاءة، القابلية للتوسع، التعامل مع الحالات الحدّية، والتنظيم. في هذا المستوى فقط يمكن اعتبار ضعف التصميم أو الكفاءة سببًا للخصم.

أي خصم يجب أن يكون بسبب خطأ تقني واضح مثبت من الكود نفسه.

تحليل المنطق:
اشرح باختصار ما يفعله الكود خطوة بخطوة مع الإشارة لأجزاء واضحة مثل main أو if أو for. لا تفترض سلوكًا غير موجود.

الأخطاء والملاحظات:
اذكر فقط الأخطاء المؤكدة من الكود. إذا لم توجد أخطاء اكتب حرفيًا:
لا توجد أخطاء مؤكدة ضمن حدود الكود المعروض.

التحسينات:
اقترح فقط تحسينات تقنية حقيقية لها أثر واضح. لا تقترح تحسينات شكلية. إذا لا توجد تحسينات جوهرية اكتب حرفيًا:
لا توجد تحسينات جوهرية مثبتة تقنيًا في حدود الكود المعروض.

قيود صارمة:
- لا تستخدم LaTeX.
- لا تخصم درجة بدون ذكر خطأ مثبت.
- إذا ذكرت عدم وجود أخطاء فلا يجوز أن يكون التقييم أقل من 9/10.
- يمنع التناقض بين الدرجة وقسم الأخطاء.

اكتب الرد كنص عادي بدون Markdown أو رموز خاصة.
"""

VALIDATION_SYSTEM_PROMPT = """
أنت مدقق جودة تحديات برمجية.

مهمتك تحديد ما إذا كان التحدي التالي:
- واضح بالكامل
- غير متناقض
- أم يحتوي على غموض أو تضارب في الأمثلة

أجب بكلمة واحدة فقط:
واضح
أو
غير_واضح

لا تكتب أي شيء إضافي.
"""

# =====================================================
# دالة الاتصال بالذكاء الاصطناعي
# =====================================================

def call_ai(messages, temperature=0.7, max_tokens=DEFAULT_MAX_TOKENS):

    if not AI_API_KEY:
        return "❌ لم يتم العثور على GROQ_API_KEY في Environment Variables."

    try:
        response = requests.post(
            f"{AI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )

        response.raise_for_status()
        return clean_text(response.json()["choices"][0]["message"]["content"])

    except requests.exceptions.Timeout:
        return "انتهى وقت الاتصال بالذكاء الاصطناعي. حاول مرة أخرى."

    except requests.exceptions.RequestException as e:
        print("AI ERROR:", e)
        return "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي. حاول مرة أخرى."

# =====================================================
# توليد تحدي
# =====================================================

def generate_challenge(level):

    prompt = f"""
أنشئ تحدي برمجي مستوى {level}.
لا تكتب الحل.
اكتب فقط:
- عنوان
- وصف واضح غير غامض
- مثال إدخال وإخراج
"""

    messages = [
        {"role": "system", "content": "أنت خبير في إنشاء تحديات برمجية دقيقة."},
        {"role": "user", "content": prompt}
    ]

    return call_ai(messages, temperature=0.7, max_tokens=800)

# =====================================================
# التحقق من وضوح التحدي
# =====================================================

def validate_challenge(challenge_text):

    messages = [
        {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
        {"role": "user", "content": challenge_text}
    ]

    result = call_ai(messages, temperature=0, max_tokens=10)
    result = result.strip().split()[0]

    return result == "واضح"

# =====================================================
# تقييم كود المستخدم
# =====================================================

def evaluate_code(level, challenge, user_code):

    user_prompt = f"""
هذا هو التحدي:
{challenge}

هذا هو كود المستخدم:
{user_code}

المستوى:
{level}
"""

    messages = [
        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    return call_ai(messages, temperature=0.1, max_tokens=800)

# ==============================
# التعامل مع الرسائل
# ==============================

def handle_message(user_id, message_text):

    if message_text in ["سهل", "متوسط", "صعب"]:

        for _ in range(3):
            challenge = generate_challenge(message_text)

            if validate_challenge(challenge):
                user_states[user_id] = {
                    "challenge": challenge,
                    "level": message_text,
                    "waiting_for_code": True
                }
                return challenge + "\n\n💻 أرسل الكود الخاص بك الآن."

        return "تعذر توليد تحدي واضح بعد عدة محاولات. حاول مرة أخرى."

    if user_id in user_states and user_states[user_id]["waiting_for_code"]:

        challenge = user_states[user_id]["challenge"]
        level = user_states[user_id]["level"]

        evaluation = evaluate_code(level, challenge, message_text)

        del user_states[user_id]
        return evaluation

    return "اختر مستوى: سهل - متوسط - صعب"
