from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import csv, datetime, os, requests, threading, urllib3, json, unicodedata, re
from bs4 import BeautifulSoup

app = Flask(__name__)

# Wyłączamy ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# “Norge” + 5 największych regionów (kody Finn.no)
cities = {
    "Norge":           "",
    "Oslo":            "0.20061",
    "Agder":           "0.22042",
    "Akershus":        "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag":       "0.20016"
}

categories = {
    "leiligheter": "1",
    "eneboliger": "2",
    "tomter":      "3"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def slugify(name):
    """Usuń diakrytyki i zamień na slug (np. 'Møre og Romsdal' → 'more-og-romsdal')."""
    nfkd = unicodedata.normalize('NFKD', name)
    no_acc = "".join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zA-Z0-9]+', '-', no_acc).strip('-').lower()

def scrape_finn(city_code, cat_code):
    if city_code:
        url = f"https://www.finn.no/realestate/homes/search.html?location={city_code}&property_type={cat_code}"
    else:
        url = f"https://www.finn.no/realestate/homes/search.html?property_type={cat_code}"
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "description"})
        if meta:
            m = re.search(r"Du finner ([\d\s\u00a0]+) boliger", meta["content"])
            if m:
                return int(m.group(1).replace("\xa0","").replace(" ",""))
    except Exception as e:
        print(f"[Finn] {url} error: {e}")
    return 0

def scrape_hjem(city_name, category_name):
    """
    Pobiera totalCount z oficjalnego API Hjem.no:
    https://hjem.no/api/v1/listings/search?availability=available&propertyType=<slug>&region=<slug>
    """
    # Kategoria: leilighet, enebolig, tomt
    cat_map = {"leiligheter":"leilighet","eneboliger":"enebolig","tomter":"tomt"}
    cat_slug = cat_map[category_name]
    params = {
        "availability": "available",
        "propertyType": cat_slug,
        "pageSize": 1,
        "page": 1
    }
    if city_name != "Norge":
        params["region"] = slugify(city_name)

    url = "https://hjem.no/api/v1/listings/search"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
        r.raise_for_status()
        data = r.json()
        return int(data.get("totalCount", 0))
    except Exception as e:
        print(f"[Hjem-API] {url} params={params} error: {e}")
    return 0

def scrape_data():
    today = datetime.date.today().isoformat()
    filename = "data.csv"
    fieldnames = ["date","city","category","finn","hjem","total"]

    if not os.path.exists(filename):
        with open(filename, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for city, code in cities.items():
            for cat, catcode in categories.items():
                finn_cnt = scrape_finn(code, catcode)
                hjem_cnt = scrape_hjem(city, cat)
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": cat,
                    "finn": finn_cnt,
                    "hjem": hjem_cnt,
                    "total": finn_cnt + hjem_cnt
                })

# Harmonogram: codziennie o 6:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_data, 'cron', hour=6)
scheduler.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    with open("data.csv", newline="") as f:
        return jsonify(list(csv.DictReader(f)))

@app.route("/force-scrape")
def force_scrape():
    # uruchamiamy scraper w tle, aby endpoint nie timeoutował
    threading.Thread(target=scrape_data).start()
    return "Scraping uruchomiony w tle.", 202

# Pierwsze uruchomienie na starcie
scrape_data()
