import requests
from bs4 import BeautifulSoup
import csv, os, datetime, re

# ścieżka do CSV
DATA_PATH = "data.csv"

# nagłówki
HEADERS_HTML = {"User-Agent": "Mozilla/5.0"}

# mapowania regionów
FINN_REGIONS = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016",
}
HJEM_SLUGS = {
    "Norge": None,
    "Oslo": "oslo",
    "Agder": "agder",
    "Akershus": "akershus",
    "Møre og Romsdal": "more-og-romsdal",
    "Trøndelag": "trondelag",
}
# kategorie: (finn_code, hjem_slug)
CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger":  ("2", "enebolig"),
    "tomter":      ("3", "tomt"),
}

def only_digits(s):
    return re.sub(r"\D", "", s)

def scrape_finn(region_code, category_code):
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=10)
        r.raise_for_status()
        meta = BeautifulSoup(r.text, "html.parser") \
               .find("meta", {"name": "description"})
        if meta and "boliger til salgs" in meta["content"]:
            # np. "Du finner 4 169 boliger til salgs..."
            text = meta["content"].split("boliger til salgs")[0]
            digits = only_digits(text)
            return int(digits) if digits else 0
    except Exception as e:
        print("[Finn] error:", e)
    return 0

def scrape_hjem(region, category_slug):
    # zawsze GET na /list?keywords=<slug>
    slug = HJEM_SLUGS.get(region)
    if slug:
        url = f"https://hjem.no/list?keywords={slug}"
    else:
        url = "https://hjem.no/list"
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "head:count"})
        if meta and meta.get("content", "").isdigit():
            return int(meta["content"])
    except Exception as e:
        print("[Hjem] error:", e)
    return 0

def save_data():
    today = datetime.date.today().isoformat()
    # przygotuj plik
    headers = ["date","city","category","finn","hjem","total"]
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=headers).writeheader()
    # dopisz
    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        for city, finn_code in FINN_REGIONS.items():
            for cat, (finn_cat, hjem_cat) in CATEGORIES.items():
                fcnt = scrape_finn(finn_code, finn_cat)
                hcnt = scrape_hjem(city, hjem_cat)
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": cat,
                    "finn": fcnt,
                    "hjem": hcnt,
                    "total": fcnt + hcnt
                })

if __name__ == "__main__":
    save_data()
