# scrape.py

import requests
import csv
import datetime
import os
from bs4 import BeautifulSoup

# ścieżka do pliku z danymi
DATA_PATH = "data.csv"

# słowniki z kodami regionów dla Finn.no i slugami regionów dla Hjem.no API
REGION_CODES = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016"
}
HOME_REGION_SLUGS = {
    "Norge": None,
    "Oslo": "oslo",
    "Agder": "agder",
    "Akershus": "akershus",
    "Møre og Romsdal": "more-og-romsdal",
    "Trøndelag": "trondelag"
}

# kategorie: (kod na Finn, slug na Hjem)
CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt")
}

# zawsze podawaj User-Agent, żeby nikt Cię nie zablokował
HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_finn(region_code, category_code):
    """Zwraca liczbę ogłoszeń z FINN.no dla danego regionu i kategorii."""
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", {"name": "description"})
    if meta and "annonser" in meta["content"]:
        # np. "Du finner 3 846 annonser …"
        raw = meta["content"].split(" annonser")[0]
        digits = "".join(filter(str.isdigit, raw))
        return int(digits) if digits else 0
    return 0

def scrape_hjem(region, property_slug):
    """Zwraca liczbę ogłoszeń z Hjem.no przez ich publiczne API."""
    slug = HOME_REGION_SLUGS.get(region)
    url = "https://www.hjem.no/api/v1/listings/search"
    params = {
        "availability": "available",
        "propertyType": property_slug,
        "pageSize": 1,
        "page": 1
    }
    if slug:
        params["region"] = slug
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    # totalCount to łączna liczba wyników
    return data.get("totalCount", 0)

def scrape_data():
    """Zbiera dane i dokleja je do data.csv."""
    today = datetime.date.today().isoformat()
    # jeśli plik nie istnieje, stwórz nagłówki
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date","city","category","finn","hjem","total"])
            writer.writeheader()

    # doklej po jednym wierszu na każdą parę (region, kategoria)
    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date","city","category","finn","hjem","total"])
        for region, finn_code in REGION_CODES.items():
            for cat, (fk, hs) in CATEGORIES.items():
                finn_cnt = scrape_finn(finn_code, fk)
                hjem_cnt = scrape_hjem(region, hs)
                writer.writerow({
                    "date": today,
                    "city": region,
                    "category": cat,
                    "finn": finn_cnt,
                    "hjem": hjem_cnt,
                    "total": finn_cnt + hjem_cnt
                })

if __name__ == "__main__":
    scrape_data()
