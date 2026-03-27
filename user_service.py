from database import get_cursor, conn

# =========================
# Save User
# =========================

def save_user(chat_id, first_name, last_name, username):
    try:
        cur = get_cursor()

        cur.execute("""
            INSERT INTO users (chat_id, first_name, last_name, username)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO NOTHING
        """, (chat_id, first_name, last_name, username))

        conn.commit()
        cur.close()

    except Exception as e:
        print("DB Error:", e)


# =========================
# Get All Users
# =========================

def get_all_users():
    try:
        cur = get_cursor()

        cur.execute("SELECT chat_id FROM users")
        users = [row[0] for row in cur.fetchall()]

        cur.close()
        return users

    except Exception as e:
        print("DB Error:", e)
        return []
