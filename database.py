import psycopg2
from config import DATABASE_URL

# =========================
# Database Connection
# =========================

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Database connected successfully.")
except Exception as e:
    print("Database connection failed:", e)
    exit()

# =========================
# Helper: get cursor
# =========================

def get_cursor():
    return conn.cursor()

# =========================
# Create Tables
# =========================

def create_tables():
    try:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            first_name TEXT,
            username TEXT,
            message_text TEXT,
            created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')
        )
        """)

        conn.commit()
        cur.close()

        print("Tables checked/created successfully.")

    except Exception as e:
        print("Error creating tables:", e)

# =========================
# Run on import
# =========================

create_tables()
