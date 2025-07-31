# scraper.py
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://archive.mozilla.org/pub/firefox/candidates/"


def get_available_versions():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    versions = []

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href.endswith("-candidates/"):
            versions.append(href.rstrip("/"))

    return sorted(versions, reverse=True)


def get_latest_build_folder(version):
    url = f"{BASE_URL}{version}/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    builds = [a.text.strip("/") for a in soup.find_all("a") if a.text.startswith("build")]
    if builds:
        return builds[-1]  # get the latest (highest number)
    return None
