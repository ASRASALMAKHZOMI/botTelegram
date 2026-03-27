import psycopg2
from config import DATABASE_URL

# =========================
# Create new connection every time
# =========================

def get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )

# =========================
# Execute (INSERT / UPDATE / DELETE)
# =========================

def execute(query, params=None):
    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(query, params)
        conn.commit()

    except Exception as e:
        print("DB ERROR:", e)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# =========================
# Fetch one result
# =========================

def fetch_one(query, params=None):
    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(query, params)
        result = cur.fetchone()
        return result

    except Exception as e:
        print("DB ERROR:", e)
        return None

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# =========================
# Fetch all results
# =========================

def fetch_all(query, params=None):
    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(query, params)
        result = cur.fetchall()
        return result

    except Exception as e:
        print("DB ERROR:", e)
        return []

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# =========================
# Create Tables
# =========================

def create_tables():
    conn = None
    cur = None

    try:
        conn = get_conn()
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
        print("Tables checked/created successfully.")

    except Exception as e:
        print("Error creating tables:", e)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# =========================
# Run on import
# =========================

create_tables()
