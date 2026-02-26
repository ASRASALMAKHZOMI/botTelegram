import os

# =========================
# Environment Variables
# =========================

TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

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
