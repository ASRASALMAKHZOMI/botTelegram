import psycopg2
import time
from psycopg2.pool import SimpleConnectionPool
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from config import DATABASE_URL


# =========================
# تنظيف الرابط
# =========================

def clean_database_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "channel_binding" in query:
        del query["channel_binding"]

    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


# =========================
# Connection Pool 🔥
# =========================

clean_url = clean_database_url(DATABASE_URL)

pool = SimpleConnectionPool(
    3, 12,   # 🔥 تقدر تتحمل 12 اتصال
    dsn=clean_url
)


def get_conn():
    return pool.getconn()


def put_conn(conn):
    pool.putconn(conn)


# =========================
# Execute
# =========================

def execute(query, params=None):
    for i in range(3):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute(query, params)
            conn.commit()
            return

        except Exception as e:
            print(f"DB ERROR (execute) attempt {i+1}:", e)
            time.sleep(1)

        finally:
            if cur:
                cur.close()
            if conn:
                put_conn(conn)   # 🔥 بدل close


# =========================
# Fetch one
# =========================

def fetch_one(query, params=None):
    for i in range(3):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute(query, params)
            return cur.fetchone()

        except Exception as e:
            print(f"DB ERROR (fetch_one) attempt {i+1}:", e)
            time.sleep(1)

        finally:
            if cur:
                cur.close()
            if conn:
                put_conn(conn)

    return None


# =========================
# Fetch all
# =========================

def fetch_all(query, params=None):
    for i in range(3):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute(query, params)
            return cur.fetchall()

        except Exception as e:
            print(f"DB ERROR (fetch_all) attempt {i+1}:", e)
            time.sleep(1)

        finally:
            if cur:
                cur.close()
            if conn:
                put_conn(conn)

    return []


# =========================
# Create Tables
# =========================

def create_tables():
    for i in range(3):
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
            print("✅ Tables checked/created successfully.")
            return

        except Exception as e:
            print(f"⚠️ DB ERROR (create_tables) attempt {i+1}:", e)
            time.sleep(2)

        finally:
            if cur:
                cur.close()
            if conn:
                put_conn(conn)

    print("❌ Failed to create tables after retries")


# =========================
# Run on import
# =========================

create_tables()
