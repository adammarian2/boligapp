import requests
import re
import csv
import datetime
import os
from bs4 import BeautifulSoup

DATA_PATH = "data.csv"

# region_name -> FINN location code
REGION_CODES = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016",
}

# your three categories
CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt"),
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_finn(region_code, category_code):
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "description"})
        if meta:
            txt = meta["content"]
            # look for e.g. "Du finner 4 169 boliger"
            m = re.search(r"([\d\u00A0 ]+)\s+boliger", txt)
            if m:
                num = m.group(1).replace("\u00A0", "").replace(" ", "")
                return int(num)
    except Exception:
        pass
    return 0

def scrape_hjem(region_name, category_slug):
    # build the path
    if region_name == "Norge":
        url = f"https://hjem.no/kjop/{category_slug}"
    else:
        part = region_name.lower().replace(" ", "-")
        url = f"https://hjem.no/kjop/{part}/{category_slug}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # try API first if it exists
        api_url = "https://hjem.no/api/v1/listings/search"
        params = {"availability":"available","propertyType":category_slug,"pageSize":1,"page":1}
        if region_name != "Norge":
            params["region"] = region_name.lower().replace(" ", "-")
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=5)
        if resp.headers.get("Content-Type","").startswith("application/json"):
            data = resp.json()
            return data.get("totalCount", 0)
        # fallback: scrape on-page "X resultater"
        text = soup.get_text()
        m = re.search(r"([\d\u00A0 ]+)\s+resultater", text)
        if m:
            num = m.group(1).replace("\u00A0", "").replace(" ", "")
            return int(num)
    except Exception:
        pass
    return 0

def save_data():
    today = datetime.date.today().isoformat()
    # ensure CSV
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date","city","category","finn","hjem","total"])
            writer.writeheader()
    # append one row per region/category
    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date","city","category","finn","hjem","total"])
        for city, code in REGION_CODES.items():
            for cat, (finn_code, hjem_slug) in CATEGORIES.items():
                fc = scrape_finn(code, finn_code)
                hc = scrape_hjem(city, hjem_slug)
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": cat,
                    "finn": fc,
                    "hjem": hc,
                    "total": fc + hc
                })
