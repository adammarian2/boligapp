import csv
import datetime
import os
import requests
from bs4 import BeautifulSoup

# Ścieżka do CSV z danymi
DATA_PATH = "data.csv"

# Kody regionów dla Finn
FINN_REGIONS = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016",
}

# Kategorie: (kod Finn, slug Hjem)
CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def scrape_finn(region_code, category_code):
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "description"})
        if meta and "boliger" in meta["content"]:
            num = "".join(filter(str.isdigit, meta["content"].split(" ")[0]))
            return int(num)
    except Exception as e:
        print("[Finn]", url, "error:", e)
    return 0


def scrape_hjem(region_name, category_slug):
    """
    Pobiera liczbę ofert z Hjem API. Jeśli region_name == "Norge", pomija parametr region.
    """
    api_url = "https://hjem.no/api/v1/listings/search"
    params = {
        "availability": "available",
        "propertyType": category_slug,
        "pageSize": 1,
        "page": 1,
    }
    if region_name != "Norge":
        # slugify regiony: usuń norweskie znaki i zamień spacje na '-'
        slug = region_name.lower()
        for c, r in [("æ","ae"),("ø","o"),("å","a")]:
            slug = slug.replace(c, r)
        slug = slug.replace(" ", "-")
        params["region"] = slug

    try:
        r = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        # odpowiedź: data["pagination"]["totalElements"]
        return data.get("pagination", {}).get("totalElements", 0)
    except Exception as e:
        print("[Hjem-API]", api_url, "params=", params, "error:", e)
    return 0


def save_data():
    """Grabisz dane z Finn i Hjem i dorzucasz do data.csv."""
    today = datetime.date.today().isoformat()
    fn = DATA_PATH
    fieldnames = ["date", "city", "category", "finn", "hjem", "total"]

    # jeśli nie ma pliku, stwórz nagłówek
    if not os.path.exists(fn):
        with open(fn, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    with open(fn, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for region, code in FINN_REGIONS.items():
            for cat, (finn_code, hjem_slug) in CATEGORIES.items():
                fcnt = scrape_finn(code, finn_code)
                hcnt = scrape_hjem(region, hjem_slug)
                writer.writerow({
                    "date": today,
                    "city": region,
                    "category": cat,
                    "finn": fcnt,
                    "hjem": hcnt,
                    "total": fcnt + hcnt
                })
