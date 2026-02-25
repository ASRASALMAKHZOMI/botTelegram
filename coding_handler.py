from state import USER_STATE
from telegram_sender import send_message, remove_keyboard
from ai_service import generate_challenge, evaluate_code, call_ai


# =========================
# Coding Challenge Handler
# =========================

def handle_coding(chat_id, text):

    current_state = USER_STATE.get(chat_id)

    # =========================
    # اختيار مستوى التحدي
    # =========================

    if current_state == "coding_level":

        if text == "🔙 رجوع":
            USER_STATE[chat_id] = "main"
            return False

        level_map = {
            "🟢 سهل": "سهل",
            "🟡 متوسط": "متوسط",
            "🔴 صعب": "صعب"
        }

        if text not in level_map:
            return False

        level = level_map[text]

        send_message(chat_id, "جاري إنشاء التحدي...")
        challenge = generate_challenge(level)

        USER_STATE[chat_id] = "coding_wait_code"
        USER_STATE[chat_id + "_challenge"] = challenge

        send_message(chat_id, challenge)
        remove_keyboard(chat_id, "💻 أرسل الكود الخاص بك الآن.")

        return True


    # =========================
    # انتظار الكود من المستخدم
    # =========================

    if current_state == "coding_wait_code":

        challenge = USER_STATE.get(chat_id + "_challenge")

        if not challenge:
            USER_STATE[chat_id] = "main"
            return False

        code_text = text.strip()

        if len(code_text) < 5:
            send_message(chat_id, "❌ أرسل الكود كاملاً.")
            return True

        # 🔎 التحقق أن النص كود فعلي
        validation_messages = [
            {
                "role": "system",
                "content": "إذا كان النص التالي كود برمجي أجب فقط بالرقم 1. إذا لم يكن كوداً أجب فقط بالرقم 0. لا تكتب أي شيء آخر."
            },
            {
                "role": "user",
                "content": code_text
            }
        ]

        validation_result = call_ai(validation_messages).strip()

        if validation_result != "1":
            send_message(chat_id, "❌ لم يتم اكتشاف كود برمجي فعلي.")
            return True

        # ✅ تقييم الحل
        send_message(chat_id, "جاري تقييم الحل...")
        evaluation = evaluate_code(challenge, code_text)

        send_message(chat_id, evaluation)

        # إعادة المستخدم لاختيار مستوى جديد
        USER_STATE[chat_id] = "coding_level"
        USER_STATE.pop(chat_id + "_challenge", None)

        keyboard = [
            ["🟢 سهل"],
            ["🟡 متوسط"],
            ["🔴 صعب"],
            ["🔙 رجوع"]
        ]

        send_message(chat_id, "اختر مستوى التحدي:", keyboard)

        return True


    return False