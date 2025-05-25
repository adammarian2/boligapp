from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import csv, datetime, os, requests, re, threading, urllib3, json, unicodedata
from bs4 import BeautifulSoup

app = Flask(__name__)

# Wyłącz ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def slugify(name):
    # usuń diakrytyki, zamień wszystko poza alfanum na '-', zbij do jednej myślnika
    nfkd = unicodedata.normalize('NFKD', name)
    no_acc = "".join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', no_acc).strip('-').lower()
    return slug

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
            txt = meta["content"]
            m = re.search(r"Du finner ([\d\s\u00a0]+) boliger", txt)
            if m:
                return int(m.group(1).replace("\xa0","").replace(" ",""))
    except Exception as e:
        print(f"[Finn] {url} error: {e}")
    return 0

def scrape_hjem(city_name, category_name):
    # slug kategorii
    cat_slug = {"leiligheter":"leilighet","eneboliger":"enebolig","tomter":"tomt"}[category_name]
    # zbuduj URL
    if city_name == "Norge":
        url = f"https://hjem.no/kjop/{cat_slug}"
    else:
        city_slug = slugify(city_name)
        url = f"https://hjem.no/kjop/{city_slug}/{cat_slug}"
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # 1) <h2> z liczbą
        h2 = soup.find("h2")
        if h2:
            digits = ''.join(filter(str.isdigit, h2.text))
            if digits:
                return int(digits)

        # 2) meta-description
        meta = soup.find("meta", {"name": "description"})
        if meta and "annonser" in meta.get("content",""):
            txt = meta["content"]
            m = re.search(r"([\d\s\u00a0]+)", txt)
            if m:
                return int(m.group(1).replace("\xa0","").replace(" ",""))

        # 3) JSON-LD fallback
        ld = soup.find("script", type="application/ld+json")
        if ld:
            try:
                j = json.loads(ld.string)
                if isinstance(j, dict) and j.get("numberOfItems"):
                    return int(j["numberOfItems"])
            except Exception:
                pass

    except Exception as e:
        print(f"[Hjem] {url} error: {e}")
    return 0

def scrape_data():
    today = datetime.date.today().isoformat()
    fn = "data.csv"
    fields = ["date","city","category","finn","hjem","total"]
    if not os.path.exists(fn):
        with open(fn, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()
    with open(fn, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
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

# scheduler 6:00 codziennie
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
    threading.Thread(target=scrape_data).start()
    return "Scraping uruchomiony w tle.", 202

# przy starcie
scrape_data()
