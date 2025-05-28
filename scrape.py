# scrape.py

import csv
import datetime
import os
import re
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ReadTimeout, RequestException

# ── KONFIG ─────────────────────────────────────────────────────
REGION_CODES = {
    "Norge":     None,
    "Oslo":      "0.20061",
    "Agder":     "0.22042",
    "Akershus":  "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016"
}

CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger":  ("2", "enebolig"),
    "tomter":      ("3", "tomt")
}

HEADERS = {"User-Agent": "Mozilla/5.0"}
DATA_PATH = "data.csv"

# ── SCRAPER FINN ───────────────────────────────────────────────
def scrape_finn(region_code, prop_code):
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={prop_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        # 5s na połączenie, 5s na odbiór każdego chunka
        r = requests.get(url, headers=HEADERS, timeout=(5, 5))
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        desc = soup.find("meta", {"name": "description"})
        content = desc["content"] if desc else ""
        m = re.search(r"([\d\s\u00a0]+)\s+boliger", content)
        if m:
            return int(m.group(1).replace("\xa0","").replace(" ",""))
    except ReadTimeout:
        print(f"[Finn] timeout przy pobieraniu {url}")
    except RequestException as e:
        print(f"[Finn] błąd request {url}: {e}")
    except Exception as e:
        print(f"[Finn] nieoczekiwany błąd {url}: {e}")
    return 0

# ── SCRAPER HJEM ──────────────────────────────────────────────
def scrape_hjem(region_name, cat_slug):
    if region_name == "Norge":
        url = f"https://www.hjem.no/kjop/{cat_slug}"
    else:
        url = f"https://www.hjem.no/kjop/{region_name.lower()}/{cat_slug}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=(5, 5))
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "head:count"})
        if meta and meta.get("content", "").isdigit():
            return int(meta["content"])
    except ReadTimeout:
        print(f"[Hjem] timeout przy pobieraniu {url}")
    except RequestException as e:
        print(f"[Hjem] błąd request {url}: {e}")
    except Exception as e:
        print(f"[Hjem] nieoczekiwany błąd {url}: {e}")
    return 0

# ── ZAPIS DANYCH ───────────────────────────────────────────────
def save_data():
    today = datetime.date.today().isoformat()
    # utwórz plik z nagłówkiem, jeśli nie istnieje
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            csv.DictWriter(
                f,
                fieldnames=["date","city","category","finn","hjem","total"]
            ).writeheader()

    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date","city","category","finn","hjem","total"]
        )
        for city, code in REGION_CODES.items():
            for cat, (finn_code, hjem_slug) in CATEGORIES.items():
                fcnt = scrape_finn(code, finn_code)
                hcnt = scrape_hjem(city, hjem_slug)
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": cat,
                    "finn": fcnt,
                    "hjem": hcnt,
                    "total": fcnt + hcnt
                })
