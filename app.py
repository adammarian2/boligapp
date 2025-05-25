from flask import Flask, render_template, jsonify, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import csv
import datetime
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

regions = {
    "Norge": None,
    "Oslo": "0.20061",
    "Agder": "0.22042",
    "Akershus": "0.20003",
    "Møre og Romsdal": "0.20015",
    "Trøndelag": "0.20016"
}

categories = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt")
}

def scrape_finn(region_code, category_code):
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "description"})
        if meta and "annonser" in meta["content"]:
            count = ''.join(filter(str.isdigit, meta["content"].split(" annonser")[0]))
            return int(count)
    except Exception as e:
        print("[Finn]", url, "error:", e)
    return 0

def scrape_hjem(region_name, category_slug):
    if region_name == "Norge":
        url = f"https://www.hjem.no/kjop/{category_slug}"
    else:
        url = f"https://www.hjem.no/kjop/{region_name.lower()}/{category_slug}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", {"name": "head:count"})
        if meta and meta.get("content", "").isdigit():
            return int(meta["content"])
    except Exception as e:
        print("[Hjem]", url, "error:", e)
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
        for region, code in regions.items():
            for cat, (finn_code, hjem_slug) in categories.items():
                finn_count = scrape_finn(code, finn_code)
                hjem_count = scrape_hjem(region, hjem_slug)
                writer.writerow({
                    "date": today,
                    "city": region,
                    "category": cat,
                    "finn": finn_count,
                    "hjem": hjem_count,
                    "total": finn_count + hjem_count
                })

scheduler = BackgroundScheduler()
scheduler.add_job(scrape_data, "cron", hour=6)
scheduler.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    with open("data.csv", newline="") as f:
        return jsonify(list(csv.DictReader(f)))

@app.route("/export")
def export():
    return send_file("data.csv", as_attachment=True)

@app.route("/force-scrape")
def force():
    scrape_data()
    return "Scraping completed."

# uruchamiamy 1 raz przy starcie
scrape_data()
