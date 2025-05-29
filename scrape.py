import requests
from bs4 import BeautifulSoup
import re
import csv
import datetime
import os

# stałe
HEADERS = {"User-Agent": "Mozilla/5.0"}
DATA_PATH = "data.csv"

REGION_CODES = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016"
}

CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt")
}

def scrape_finn(region_code: str, category_code: str) -> int:
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        meta = BeautifulSoup(r.text, "html.parser").find("meta", {"name": "description"})
        if not meta:
            return 0
        content = meta["content"]
        # szukamy "Du finner X bolig..."
        m = re.search(r"Du finner\s([\d\s\xa0]+)\sbolig", content)
        if m:
            num = m.group(1).replace("\xa0","").replace(" ","")
            return int(num)
    except Exception as e:
        print("[Finn]", url, "error:", e)
    return 0

def scrape_hjem(region: str, category_slug: str) -> int:
    # Hjem: liczba "X treff" na stronie list
    # budujemy URL: /list?keywords={region}+{category}
    base = "https://hjem.no"
    if region == "Norge":
        url = f"{base}/list?keywords={category_slug}"
    else:
        slug = region.lower().replace(" ", "%20")
        url = f"{base}/list?keywords={slug}%20{category_slug}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        text = r.text
        m = re.search(r"([\d\s\xa0]+)\s+treff", text)
        if m:
            num = m.group(1).replace("\xa0","").replace(" ","")
            return int(num)
    except Exception as e:
        print("[Hjem]", url, "error:", e)
    return 0

def save_data():
    today = datetime.date.today().isoformat()
    # jeśli plik nie istnieje, stwórz z nagłówkiem
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date","city","category","finn","hjem","total"])
    # dopisujemy
    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        for city, code in REGION_CODES.items():
            for cat, (finn_code, hjem_slug) in CATEGORIES.items():
                fcnt = scrape_finn(code, finn_code)
                hcnt = scrape_hjem(city, hjem_slug)
                writer.writerow([today, city, cat, fcnt, hcnt, fcnt+hcnt])

if __name__ == "__main__":
    save_data()
