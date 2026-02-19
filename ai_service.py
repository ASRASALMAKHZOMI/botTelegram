import os
import requests

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

    return response.json()["choices"][0]["message"]["content"]


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
    prompt = f"""
    هذا التحدي:
    {challenge}

    هذا كود المستخدم:
    {code}

    قيّم الحل من 10
    حلل المنطق
    اذكر الأخطاء
    اقترح تحسينات

    لا تهتم باللغة البرمجية.
    ركز على المنطق.
    """

    messages = [
        {"role": "system", "content": "أنت مراجع أكواد خبير."},
        {"role": "user", "content": prompt}
    ]

    return call_ai(messages)


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
