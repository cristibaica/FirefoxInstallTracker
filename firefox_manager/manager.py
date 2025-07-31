# manager.py
import os
import json
import zipfile
from datetime import datetime

DB_FILE = "firefox_db.json"
INSTALL_ROOT = "builds"

def extract_zip(zip_path, target_folder):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_folder)
    return target_folder

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(entries):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

def add_install_record(version, arch, lang, install_path):
    db = load_db()

    # Remove any existing entry with the same version, arch, and language to avoid duplicates
    db = [e for e in db if not (e["version"] == version and e["arch"] == arch and e["language"] == lang)]

    entry = {
        "version": version,
        "arch": arch,
        "language": lang,
        "install_path": install_path,
        "installed_at": datetime.now().isoformat()
    }

    db.append(entry)
    save_db(db)

def get_install_folder(version, arch, lang):
    folder_name = f"{version}-{arch}-{lang}"
    return os.path.join(INSTALL_ROOT, folder_name)