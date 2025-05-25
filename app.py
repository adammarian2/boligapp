from flask import Flask, render_template, jsonify, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import csv
import datetime
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Lista miast i odpowiadające im parametry lokalizacji (dla URLi)
cities = {
    "Oslo": "0.20061",
    "Bergen": "0.23346",
    "Stavanger": "0.20216",
    "Trondheim": "0.20084",
    "Drammen": "0.20174"
}

# Kategorie: leiligheter=1, eneboliger=2, tomter=3
categories = {
    "leiligheter": "1",
    "eneboliger": "2",
    "tomter": "3"
}

# Scraper dla Finn.no – z meta tagu description
def scrape_finn(city_code, category_code):
    url = f"https://www.finn.no/realestate/homes/search.html?location={city_code}&property_type={category_code}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        meta_tag = soup.find("meta", {"name": "description"})
        if meta_tag and "annonser" in meta_tag.get("content", ""):
            text = meta_tag["content"]
            number = int(''.join(filter(str.isdigit, text.split(" annonser")[0])))
            return number
    except Exception as e:
        print(f"Finn scraping error: {e}")
    return 0

# Scraper dla Hjem.no
def scrape_hjem(city_name, category_name):
    cat_map = {
        "leiligheter": "leilighet",
        "eneboliger": "enebolig",
        "tomter": "tomt"
    }
    category_slug = cat_map.get(category_name, category_name)
    url = f"https://www.hjem.no/kjop/{city_name.lower()}/{category_slug}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        header = soup.find("h2")
        if header:
            return int(''.join(filter(str.isdigit, header.text)))
    except Exception as e:
        print(f"Hjem scraping error: {e}")
    return 0

# Główna funkcja scrapująca dane
def scrape_data():
    today = datetime.date.today().isoformat()
    filename = "data.csv"
    fieldnames = ["date", "city", "category", "finn", "hjem", "total"]

    if not os.path.exists(filename):
        with open(filename, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    with open(filename, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for city, city_code in cities.items():
            for category, category_code in categories.items():
                finn_count = scrape_finn(city_code, category_code)
                hjem_count = scrape_hjem(city, category)
                total = finn_count + hjem_count
                writer.writerow({
                    "date": today,
                    "city": city,
                    "category": category,
                    "finn": finn_count,
                    "hjem": hjem_count,
                    "total": total
                })

# Harmonogram
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_data, 'cron', hour=6)
scheduler.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def get_data():
    filename = "data.csv"
    rows = []
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return jsonify(rows)

@app.route("/export")
def export():
    return send_file("data.csv", as_attachment=True)

@app.route("/force-scrape")
def force_scrape():
    scrape_data()
    return "Scraping completed manually."

# NIE URUCHAMIAMY app.run() – Render używa gunicorn app:app
scrape_data()
