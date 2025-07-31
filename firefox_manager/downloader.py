import os
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://archive.mozilla.org/pub/firefox/candidates/"

def get_latest_build(version):
    """Return the latest build folder (e.g. build1, build2) for a given version"""
    url = f"{BASE_URL}{version}/"
    res = requests.get(url)
    if res.status_code != 200:
        raise Exception(f"Failed to access version folder: {url}")

    soup = BeautifulSoup(res.text, "html.parser")
    builds = []

    for a in soup.find_all("a"):
        href = a.get("href", "")
        # href can be absolute path like /pub/firefox/candidates/141.0b3-candidates/build1/
        if href.endswith("/") and "/build" in href:
            folder_name = href.strip("/").split("/")[-1]
            if folder_name.startswith("build"):
                try:
                    num = int(folder_name.replace("build", ""))
                    builds.append((num, folder_name))
                except ValueError:
                    continue

    if not builds:
        raise Exception(f"No build folders (like build1/) found at:\n{url}")

    builds.sort()
    return builds[-1][1]


def download_build(version, arch, lang, dest_folder="builds", progress_callback=None):
    """
    Downloads the Firefox build zip file for given version, arch and lang.
    Supports progress_callback(percent) to report download progress (0-100).
    """
    build = get_latest_build(version)
    if not build:
        raise Exception("No build folder found")

    clean_version = version.replace("-candidates", "")

    if arch.startswith("win"):
        filename = f"firefox-{clean_version}.zip"
    elif arch == "mac":
        filename = f"Firefox {clean_version}.dmg"
    elif arch.startswith("linux"):
        filename = f"firefox-{clean_version}.tar.bz2"
    else:
        raise ValueError("Unknown architecture")

    url = f"{BASE_URL}{version}/{build}/{arch}/{lang}/{filename}"

    os.makedirs(dest_folder, exist_ok=True)
    dest_path = os.path.join(dest_folder, filename)

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download. HTTP {response.status_code}")

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    percent = downloaded / total_size * 100
                    progress_callback(percent)

    return dest_path
