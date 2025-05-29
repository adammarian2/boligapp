import requests
from bs4 import BeautifulSoup
import datetime
import csv
import os
import unicodedata

# Ścieżka do pliku z danymi
DATA_PATH = "data.csv"

# Nagłówki dla obu serwisów
HEADERS_JSON = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest"
}
HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0"
}

# Mapowania regionów i kategorii
REGION_SLUGS = {
    "Norge": None,
    "Oslo": "oslo",
    "Agder": "agder",
    "Akershus": "akershus",
    "Møre og Romsdal": "more-og-romsdal",
    "Trøndelag": "trondelag",
}
FINN_REGIONS = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016",
}
CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt"),
}

def _only_digits(s: str) -> str:
    """Usuń spacje, NBSP i inne, zostaw tylko cyfry."""
    return "".join(ch for ch in s if ch.isdigit())

def scrape_finn(region_code, category_code):
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "description"})
        if meta and "boliger til salgs" in meta["content"]:
            text = meta["content"].split("boliger til salgs")[0]
            digits = _only_digits(text)
            return int(digits)
    except Exception as e:
        print("[Finn]", url, "error:", e)
    return 0

def scrape_hjem(region_name, category_slug):
    """Pierwsza próba: API JSON. Jeśli się nie uda, fallback na statyczny HTML."""
    params = {
        "availability": "available",
        "propertyType": category_slug,
        "pageSize": 1,
        "page": 1
    }
    slug = REGION_SLUGS.get(region_name)
    if slug:
        params["region"] = slug

    # 1) Spróbuj API JSON
    try:
        r = requests.get(
            "https://hjem.no/api/v1/listings/search",
            params=params,
            headers=HEADERS_JSON,
            timeout=10
        )
        if "application/json" in r.headers.get("Content-Type", ""):
            j = r.json()
            # najczęściej jest w meta.totalItems
            count = j.get("meta", {}).get("totalItems") \
                 or j.get("meta", {}).get("count")
            if count is not None:
                return int(count)
    except Exception as e:
        print("[Hjem-API]", e)

    # 2) Fallback: statyczny HTML
    try:
        if slug:
            url = f"https://hjem.no/list?keywords={slug}"
        else:
            url = "https://hjem.no/list"
        r = requests.get(url, headers=HEADERS_HTML, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # wiele wersji: np. <h1>40 289 resultater</h1>
        h1 = soup.find("h1")
        if h1:
            digits = _only_digits(h1.get_text())
            return int(digits)
    except Exception as e:
        print("[Hjem-HTML]", url, "error:", e)

    return 0

def save_data():
    today = datetime.date.today().isoformat()
    # przygotuj plik
    fields = ["date", "city", "category", "finn", "hjem", "total"]
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()

    # dopisz nowy wiersz
    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        for city, finn_code in FINN_REGIONS.items():
            for cat, (finn_cat, hjem_slug) in CATEGORIES.items():
                finn_cnt = scrape_finn(finn_code, finn_cat)
                hjem_cnt = scrape_hjem(city, hjem_slug)
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": cat,
                    "finn": finn_cnt,
                    "hjem": hjem_cnt,
                    "total": finn_cnt + hjem_cnt
                })

if __name__ == "__main__":
    save_data()
