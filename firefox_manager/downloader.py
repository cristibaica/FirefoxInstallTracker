import os
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://archive.mozilla.org/pub/firefox/candidates/"

def get_latest_build(version):
    url = f"{BASE_URL}{version}/"
    print(f"Requesting URL: {url}")
    res = requests.get(url)
    print(f"Status code: {res.status_code}")
    print(f"Response headers: {res.headers}")
    print(f"Response text snippet:\n{res.text[:500]}")  # print first 500 chars

    if res.status_code != 200:
        raise Exception(f"Failed to access version folder: {url}")

    soup = BeautifulSoup(res.text, "html.parser")
    builds = []

    for a in soup.find_all("a"):
        href = a.get("href", "")
        print(f"Found link: {href}")
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


def get_filename(version, arch):
    """Determine filename based on platform"""
    clean_version = version.replace('-candidates', '')

    if arch.startswith("win"):
        return f"firefox-{clean_version}.zip"
    elif arch == "mac":
        return f"Firefox {clean_version}.dmg"
    elif arch.startswith("linux"):
        return f"firefox-{clean_version}.tar.bz2"
    else:
        raise ValueError("Unknown architecture")

def download_build(version, arch, lang, dest_folder="builds"):
    build = get_latest_build(version)  # version MUST still have -candidates
    if not build:
        raise Exception("No build folder found")

    # Clean version string only for the filename
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

    print(f"Downloading from: {url}")
    os.makedirs(dest_folder, exist_ok=True)
    dest_path = os.path.join(dest_folder, filename)

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download. HTTP {response.status_code}")

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return dest_path
