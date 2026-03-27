from database import execute, fetch_all

# =========================
# Save User
# =========================

def save_user(chat_id, first_name, last_name, username):
    try:
        execute("""
            INSERT INTO users (chat_id, first_name, last_name, username)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO NOTHING
        """, (chat_id, first_name, last_name, username))

    except Exception as e:
        print("DB Error:", e)


# =========================
# Get All Users
# =========================

def get_all_users():
    try:
        rows = fetch_all("SELECT chat_id FROM users")
        return [row[0] for row in rows]

    except Exception as e:
        print("DB Error:", e)
        return []
