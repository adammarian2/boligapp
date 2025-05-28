import requests
import csv
import datetime
import os
from bs4 import BeautifulSoup

DATA_PATH = "data.csv"

# kody regionów dla FINN.no
REGION_CODES = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016"
}

# Kategorie FINN: (kod)
CATEGORIES = {
    "leiligheter": "1",
    "eneboliger": "2",
    "tomter":       "3"
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_finn(region_code, category_code):
    """Zwraca liczbę ogłoszeń z FINN.no."""
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", {"name": "description"})
    if meta and "annonser" in meta["content"]:
        raw = meta["content"].split(" annonser")[0]
        digits = "".join(filter(str.isdigit, raw))
        return int(digits) if digits else 0
    return 0

def scrape_data():
    """Dokleja do data.csv po jednej linii (date, city, category, finn)."""
    today = datetime.date.today().isoformat()
    # jeśli nie ma pliku, stwórz nagłówki
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date","city","category","finn"])
            writer.writeheader()

    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date","city","category","finn"])
        for region, code in REGION_CODES.items():
            for cat, cat_code in CATEGORIES.items():
                cnt = scrape_finn(code, cat_code)
                writer.writerow({
                    "date": today,
                    "city": region,
                    "category": cat,
                    "finn": cnt
                })

if __name__ == "__main__":
    scrape_data()
