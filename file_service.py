import os
import re

# =========================
# Sort By Number
# =========================

def sort_by_number(items):
    def extract_number(name):
        base = os.path.splitext(name)[0]
        match = re.match(r"(\d+)", base)
        if match:
            return int(match.group(1))
        return 999
    return sorted(items, key=extract_number)


# =========================
# Get Sorted Files
# =========================

def get_sorted_files(path):
    try:
        files = os.listdir(path)
        return sort_by_number(files)
    except Exception as e:
        print("File Error:", e)
        return []


# =========================
# Get Subdirectories
# =========================

def get_subdirectories(path):
    try:
        return [
            f for f in os.listdir(path)
            if os.path.isdir(os.path.join(path, f))
        ]
    except Exception as e:
        print("Directory Error:", e)
        return []