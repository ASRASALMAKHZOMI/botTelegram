from database import cur, conn

# =========================
# Save User
# =========================

def save_user(chat_id, first_name, last_name, username):
    try:
        cur.execute("""
            INSERT INTO users (chat_id, first_name, last_name, username)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO NOTHING
        """, (chat_id, first_name, last_name, username))
        conn.commit()
    except Exception as e:
        print("DB Error:", e)


# =========================
# Get All Users
# =========================

def get_all_users():
    try:
        cur.execute("SELECT chat_id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("DB Error:", e)
        return []