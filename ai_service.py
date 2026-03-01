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
# Prompts
# ==============================

CHALLENGE_SYSTEM_PROMPT = """
أنت مدرس برمجة يشرح لطلاب مبتدئين.

اكتب المسائل بأسلوب بسيط جدًا مهما كان المستوى.
استخدم جمل قصيرة.
لا تستخدم أسلوب أكاديمي.
لا تستخدم كلمات معقدة.
لا تستخدم تعبيرات مثل: تحليل، معالجة، تحقق، قم بـ، تأكد من.
لا تكتب أكثر من 4 أسطر في نص المسألة.
اشرح المطلوب مباشرة بدون مقدمة.
حتى لو كانت الفكرة صعبة، يجب أن تكون القراءة سهلة جدًا.
"""

CHALLENGE_USER_TEMPLATE = """
أنشئ مسألة تدريبية مستوى {level} تركز على التفكير المنطقي فقط.

الشروط:
- لا تستخدم هياكل بيانات متقدمة.
- لا يكون السؤال متعلقًا بقواعد البيانات.
- يجب أن يكون الحل ممكنًا باستخدام شروط وحلقات بسيطة فقط.
- لا تكتب قصة.
- لا تكتب وصفًا طويلًا.

اكتب فقط بالصيغة التالية وبدون أي نص إضافي:

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

إذا لم تكتب جميع الأقسام كاملة حتى Test 3 مع Input و Output لكل واحد، أعد كتابة الرد كاملًا.

لا تكتب الحل.
لا تضف أي شرح إضافي.
"""

VALIDATION_SYSTEM_PROMPT = """
أجب فقط بكلمة واحدة:
واضح
أو
غير_واضح
"""

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

لا تستخدم Markdown.
لا تستخدم LaTeX.
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

    for _ in range(2):
        try:
            response = requests.post(
                URL,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            if "choices" not in result or not result["choices"]:
                continue

            content = result["choices"][0]["message"].get("content")
            if not content:
                continue

            return clean_text(content)

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException as e:
            print("AI ERROR:", e)
            break

    return "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي. حاول مرة أخرى."

# ==============================
# توليد تحدي
# ==============================

def generate_challenge(level):

    user_prompt = CHALLENGE_USER_TEMPLATE.format(level=level)

    messages = [
        {"role": "system", "content": CHALLENGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    required_sections = [
        "عنوان:",
        "المسألة:",
        "Input:",
        "Output:",
        "Test Cases:",
        "Test 1:",
        "Test 2:",
        "Test 3:"
    ]

    for _ in range(4):

        challenge = call_ai(messages, temperature=0.3, max_tokens=1200)

        if all(section in challenge for section in required_sections):
            if challenge.count("Input:") >= 4 and challenge.count("Output:") >= 4:
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

        return "تعذر توليد تحدي واضح. حاول مرة أخرى."

    if user_id in user_states and user_states[user_id]["waiting_for_code"]:

        challenge = user_states[user_id]["challenge"]
        evaluation = evaluate_code(challenge, message_text)

        del user_states[user_id]
        return evaluation

    return "اختر مستوى: سهل - متوسط - صعب"
