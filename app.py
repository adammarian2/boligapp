from flask import Flask, render_template, jsonify, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import csv
import datetime
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# === Regions (slug for Hjem) and Finn location codes ===
regions = {
    "Norge": None,
    "Oslo": "0.20061",
    "Bergen": "0.23346",
    "Stavanger": "0.20216",
    "Trondheim": "0.20084",
    "Drammen": "0.20174"
}

# === Categories: Finn property_type codes & Hjem slugs ===
categories = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter": ("3", "tomt")
}

def scrape_finn(region_code, prop_code):
    """Pull count from Finn.no via meta description."""
    url = f"https://www.finn.no/realestate/homes/search.html?location={region_code}&property_type={prop_code}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        desc = soup.find("meta", {"name": "description"})
        if desc and "annonser" in desc["content"]:
            # e.g. "Du finner 3 846 boliger til salg … annonser"
            num = desc["content"].split(" annonser")[0]
            return int(''.join(filter(str.isdigit, num)))
    except Exception:
        pass
    return 0

def scrape_hjem(region_name, category_slug):
    """Pull count from Hjem.no using meta[name=head:count] on the listing page."""
    # Determine URL: site-wide vs region
    if regions[region_name] is None:
        # all Norway by category
        url = f"https://www.hjem.no/kjop/{category_slug}"
    else:
        url = f"https://www.hjem.no/kjop/{region_name.lower()}/{category_slug}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        meta = soup.find("meta", {"name": "head:count"})
        if meta and meta.get("content", "").isdigit():
            return int(meta["content"])
    except Exception:
        pass
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
        for city, finn_code in regions.items():
            for cat, (finn_cat, hjem_slug) in categories.items():
                finn_cnt = scrape_finn(finn_code, finn_cat) if finn_code else scrape_finn("", finn_cat)
                hjem_cnt = scrape_hjem(city, hjem_slug)
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": cat,
                    "finn": finn_cnt,
                    "hjem": hjem_cnt,
                    "total": finn_cnt + hjem_cnt
                })

# schedule daily scrape at 06:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_data, "cron", hour=6)
scheduler.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    with open("data.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    return jsonify(rows)

@app.route("/export")
def export():
    return send_file("data.csv", as_attachment=True)

@app.route("/force-scrape")
def force():
    scrape_data()
    return "Scraping completed."

# on startup
scrape_data()
# (no app.run – Render uses gunicorn app:app)
