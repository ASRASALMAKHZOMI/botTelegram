import os
from dotenv import load_dotenv

# =========================
# Load Environment Variables
# =========================

# تحميل .env من نفس مجلد المشروع بشكل صريح
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_PATH)

# =========================
# Environment Variables
# =========================

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    print("ERROR: TOKEN not set.")
    exit()

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    exit()

# =========================
# System Settings
# =========================

MAINTENANCE_MODE = False
ADMIN_ID = "6829734732"

# =========================
# Levels Folders
# =========================

LEVEL1_FOLDER = "Level 1"
LEVEL2_FOLDER = "Files"
LEVEL3_FOLDER = "Level 3"
LEVEL4_FOLDER = "Level 4"
