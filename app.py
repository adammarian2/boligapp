from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import csv, datetime, os, requests, re, threading, urllib3
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
    # budujemy slug dla Hjem
    slug = {"leiligheter":"leilighet","eneboliger":"enebolig","tomter":"tomt"}[category_name]
    if city_name == "Norge":
        url = f"https://www.hjem.no/kjop/{slug}"
    else:
        url = f"https://www.hjem.no/kjop/{city_name.lower()}/{slug}"
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # szukamy meta description
        meta = soup.find("meta", {"name": "description"}) or soup.find("meta", {"property": "og:description"})
        if meta:
            txt = meta.get("content", "")
            # wyciągamy pierwszą grupę cyfr
            m = re.search(r"([\d\s\u00a0]+)", txt)
            if m:
                return int(m.group(1).replace("\xa0","").replace(" ",""))
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

# harmonogram
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
def force():
    # uruchom w tle żeby nie blokować
    threading.Thread(target=scrape_data).start()
    return "Scraping uruchomiony w tle.", 202

# przy starcie
scrape_data()
