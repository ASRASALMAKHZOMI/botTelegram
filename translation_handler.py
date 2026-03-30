from state import USER_STATE
from telegram_sender import send_message
from translation_queue import add_task


def handle_translation(chat_id, text, message):

    state = USER_STATE.get(chat_id)

    # =========================
    # القائمة
    # =========================
    if state == "translation_menu":

        if text == "🔙 رجوع":
            USER_STATE[chat_id] = "main"
            return False

        if text == "📂 اختيار من الملازم":
            USER_STATE[chat_id] = "translation_from_files"
            USER_STATE[chat_id + "_translation_mode"] = True
            return False

        if text == "📤 رفع ملف":
            USER_STATE[chat_id] = "translation_upload"
            send_message(chat_id, "أرسل ملف PDF")
            return True

        return True


    # =========================
    # استقبال الملف
    # =========================
    if state == "translation_upload":

        if message and "document" in message:

            file_id = message["document"]["file_id"]

            # 👇 هنا استخدمنا queue اللي سويناه
            add_task(file_id, chat_id)

            send_message(chat_id, "تم استلام الملف")

            USER_STATE[chat_id] = "main"
            return True

        return True


    return False