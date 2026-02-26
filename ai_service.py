import os
import requests
import re

# ==============================
# إعدادات
# ==============================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"

user_states = {}

# ==============================
# تنظيف آمن
# ==============================

def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text.strip()

# ==============================
# الاتصال بالذكاء
# ==============================

def call_ai(messages, temperature=0.7, max_tokens=1500):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(URL, headers=headers, json=data, timeout=30)
    response.raise_for_status()

    return clean_text(response.json()["choices"][0]["message"]["content"])

# ==============================
# توليد تحدي
# ==============================

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

    return call_ai(messages)

# ==============================
# التحقق من وضوح التحدي
# ==============================

def validate_challenge(challenge_text):

    system_prompt = """
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

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": challenge_text}
    ]

    result = call_ai(messages, temperature=0, max_tokens=10)
    result = result.strip().split()[0]

    return result == "واضح"

# ==============================
# تقييم الكود (لم يتم تعديله)
# ==============================

def evaluate_code(challenge, code):

    system_prompt = """
أنت مراجع أكواد برمجية محترف لأي لغة برمجة.
مهمتك تحليل الكود المُرسل لك اعتمادًا فقط على ما هو مكتوب فيه حرفيًا.

عند الرد، التزم بالهيكل التالي دون إضافة أقسام أخرى:

التقييم من 10:
قيّم التنفيذ التقني فقط وليس الفكرة العامة.

يجب أولًا تحديد مستوى التحدي من وصفه (بسيط، متوسط، متقدم) قبل إعطاء التقييم.

معايير التقييم حسب المستوى:

- إذا كان التحدي بسيطًا:
  يتم التركيز فقط على صحة التنفيذ والوضوح.
  لا يُنقص التقييم بسبب عدم استخدام تقنيات متقدمة.
  الحل الصحيح والواضح يستحق تقييمًا مرتفعًا.
  يتم تخفيض التقييم فقط عند وجود خطأ منطقي مثبت.

- إذا كان التحدي متوسطًا:
  يتم تقييم صحة التنفيذ، تنظيم الكود، وضوح المنطق، والتعامل مع الحالات المتوقعة.
  يمكن تخفيض التقييم عند وجود ضعف تنظيمي واضح أو إهمال حالات مهمة.

- إذا كان التحدي متقدمًا:
  يتم تقييم جودة التصميم، الكفاءة، القابلية للتوسع، التعامل مع الحالات الحدّية، وتنظيم الحل.
  في هذا المستوى فقط يمكن اعتبار ضعف التصميم أو الكفاءة سببًا لتخفيض التقييم.

يجب أن يكون أي تخفيض في التقييم مبررًا بسبب تقني واضح ومستند إلى الكود نفسه.
لا تعاقب الحلول البسيطة إذا كانت صحيحة وتؤدي المطلوب بالكامل.

تحليل المنطق:
صف ما يفعله الكود خطوة بخطوة بدقة.
اربط الشرح بأجزاء واضحة من الكود مثل: داخل main، في if، في for.
لا تفترض أي سلوك غير موجود صراحة في الكود.

الأخطاء والملاحظات:
اذكر فقط الأخطاء التي يمكن إثباتها من الكود نفسه.
لا تعتبر الاختيارات التصميمية البسيطة خطأ تقنيًا ما لم تسبب مشكلة فعلية.
إذا لم توجد أخطاء مؤكدة، اكتب حرفيًا:
لا توجد أخطاء مؤكدة ضمن حدود الكود المعروض.

التحسينات:
اقترح فقط تحسينات لها أثر تقني حقيقي وقابل للتبرير.
كل تحسين يجب أن يوضح:
- ما المشكلة الحالية؟
- لماذا هذا الاقتراح أفضل تقنيًا؟
- ما أثره الفعلي؟
لا تقترح تحسينات شكلية أو تجميلية.
إذا لم توجد تحسينات جوهرية مثبتة تقنيًا، اكتب حرفيًا:
لا توجد تحسينات جوهرية مثبتة تقنيًا في حدود الكود المعروض.

قيود صارمة إضافية:

- لا يجوز خفض التقييم دون ذكر خطأ تقني مثبت في قسم الأخطاء.
- إذا كتبت "لا توجد أخطاء مؤكدة ضمن حدود الكود المعروض."
  فلا يجوز أن يكون التقييم أقل من 9/10.
- يمنع وجود أي تناقض بين الدرجة الرقمية وقسم الأخطاء.

اكتب الرد كنص عادي بدون Markdown أو رموز خاصة.
لا تذكر أي تعليمات في الرد.
"""

    user_prompt = f"""
هذا هو التحدي:
{challenge}

هذا هو كود المستخدم:
{code}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    evaluation = call_ai(messages, temperature=0.1)

    # تحقق تناقض
    verification_prompt = f"""
راجع التقييم التالي:

{evaluation}

هل يوجد تناقض بين الدرجة الرقمية وقسم الأخطاء؟

أجب بكلمة واحدة فقط:
نعم
أو
لا
"""

    verify_messages = [
        {"role": "system", "content": "أجب فقط بكلمة واحدة: نعم أو لا."},
        {"role": "user", "content": verification_prompt}
    ]

    verification = call_ai(verify_messages, temperature=0, max_tokens=5)
    verification = verification.strip().split()[0]

    if verification == "نعم":
        return "تم اكتشاف تناقض في التقييم. أعد المحاولة."

    return evaluation

# ==============================
# التعامل مع الرسائل
# ==============================

def handle_message(user_id, message_text):

    if message_text in ["سهل", "متوسط", "صعب"]:

        # إعادة المحاولة حتى يكون واضح
        for _ in range(3):
            challenge = generate_challenge(message_text)
            if validate_challenge(challenge):
                user_states[user_id] = {
                    "challenge": challenge,
                    "waiting_for_code": True
                }
                return challenge + "\n\n💻 أرسل الكود الخاص بك الآن."

        return "تعذر توليد تحدي واضح بعد عدة محاولات. حاول مرة أخرى."

    if user_id in user_states and user_states[user_id]["waiting_for_code"]:
        challenge = user_states[user_id]["challenge"]
        evaluation = evaluate_code(challenge, message_text)

        del user_states[user_id]
        return evaluation

    return "اختر مستوى: سهل - متوسط - صعب"
