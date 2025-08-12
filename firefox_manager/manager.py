# manager.py
import os
import json
import zipfile
import tarfile
from datetime import datetime
import platform
import subprocess
import time
import shutil

DB_FILE = "firefox_db.json"
INSTALL_ROOT = "builds"

def extract_zip(zip_path, target_folder):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_folder)
    return target_folder

def extract_tar_bz2(tar_path, target_folder):
    with tarfile.open(tar_path, 'r:bz2') as tar_ref:
        tar_ref.extractall(target_folder)
    return target_folder

def extract_tar_xz(tar_path, target_folder):
    with tarfile.open(tar_path, 'r:xz') as tar_ref:
        tar_ref.extractall(target_folder)
    return target_folder

def install_dmg(dmg_path, target_folder):
    """Mounts a DMG, copies the .app to the target, and unmounts."""
    if platform.system() != 'Darwin':
        raise NotImplementedError("DMG installation is only supported on macOS.")

    # Mount the DMG without it showing up in Finder
    mount_process = subprocess.run(['hdiutil', 'attach', '-nobrowse', dmg_path], capture_output=True, text=True)
    if mount_process.returncode != 0:
        raise Exception(f"Failed to mount DMG: {mount_process.stderr}")

    mount_point = None
    try:
        # Find the mount point from the output
        for line in mount_process.stdout.splitlines():
            if '/Volumes/' in line:
                # The line looks like: /dev/disk... /Volumes/Firefox
                # We split by tab or multiple spaces and take the last part
                mount_point = line.split(None, 2)[-1].strip()
                break

        if not mount_point:
            raise Exception("Could not find mount point for DMG.")

        # Find the .app bundle in the mounted volume
        app_bundle_name = next((item for item in os.listdir(mount_point) if item.endswith('.app')), None)

        if not app_bundle_name:
            raise Exception(f"Could not find .app bundle in {mount_point}")

        # Copy the .app bundle to the target installation folder
        source_app_path = os.path.join(mount_point, app_bundle_name)
        dest_app_path = os.path.join(target_folder, app_bundle_name)
        if os.path.exists(dest_app_path):
            shutil.rmtree(dest_app_path)
        shutil.copytree(source_app_path, dest_app_path)

    finally:
        # Unmount the DMG
        if mount_point:
            time.sleep(1)  # Give a moment before detaching
            subprocess.run(['hdiutil', 'detach', mount_point], capture_output=True)

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