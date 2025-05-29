from flask import Flask, render_template, request, jsonify, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import csv, os, datetime, re
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# -------------- KONFIG -----------------
DATA_FILE = "data.csv"
# regiony z kodami FINN i nazwami Hjem
REGIONS = {
    "Norge":       {"finn": None,       "hjem": None},
    "Oslo":        {"finn": "0.20061",  "hjem": "oslo"},
    "Agder":       {"finn": "0.22042",  "hjem": "agder"},
    "Akershus":    {"finn": "0.20003",  "hjem": "akershus"},
    "Møre og Romsdal": {"finn": "0.20015", "hjem": "more-og-romsdal"},
    "Trøndelag":   {"finn": "0.20016",  "hjem": "trondelag"},
}

CATEGORIES = {
    "leiligheter": ("1", "leilighet"),
    "eneboliger": ("2", "enebolig"),
    "tomter":      ("3", "tomt"),
}

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
# ---------------------------------------

def scrape_finn(region_code, category_code):
    """Scrape liczby z FINN.no przez meta description."""
    url = f"https://www.finn.no/realestate/homes/search.html?property_type={category_code}"
    if region_code:
        url += f"&location={region_code}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", {"name": "description"})
    if not meta:
        return 0
    text = meta["content"]
    # szukamy np. "Du finner 4 169 boliger"
    m = re.search(r"Du finner\s*([\d\s]+)\s+boliger", text)
    if m:
        return int(m.group(1).replace(" ", ""))
    # czasem domy: "0 eneboliger"
    m2 = re.search(r"Du finner\s*([\d\s]+)\s+hus", text)
    if m2:
        return int(m2.group(1).replace(" ", ""))
    return 0

def scrape_hjem(region_slug, category_slug):
    """Scrape liczby z Hjem.no przez HTML wyników."""
    # jeśli region_slug=None, robimy ogólną
    if region_slug:
        url = f"https://hjem.no/list?keywords={region_slug}&type={category_slug}"
    else:
        url = f"https://hjem.no/list?keywords={category_slug}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # zakładamy, że w <h1> albo <p> jest "X resultater"
    text = soup.get_text(separator=" ").strip()
    m = re.search(r"([\d\s]+)\s+resultater", text)
    if m:
        return int(m.group(1).replace(" ", ""))
    return 0

def scrape_data():
    """Zbiera dane do CSV."""
    today = datetime.date.today().isoformat()
    # jeśli nie ma pliku, dopisujemy nagłówek
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date","region","category","finn","hjem","total"])
    with open(DATA_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        for region, codes in REGIONS.items():
            for cat, (finn_code, hjem_slug) in CATEGORIES.items():
                fcnt = scrape_finn(codes["finn"], finn_code)
                hcnt = scrape_hjem(codes["hjem"], hjem_slug)
                writer.writerow([today, region, cat, fcnt, hcnt, fcnt+hcnt])
    print(">> scrape_data done:", today)

# 1) uruchamiamy od razu
try:
    scrape_data()
except Exception as e:
    print("Error initial scrape:", e)

# 2) planujemy codziennie o 06:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_data, "cron", hour=6, minute=0)
scheduler.start()


@app.route("/")
def index():
    return render_template("index.html",
        regions=list(REGIONS.keys()),
        selected=request.args.get("region","Norge")
    )

@app.route("/data")
def data():
    """Zwraca cały CSV jako JSON listę obiektów."""
    if not os.path.exists(DATA_FILE):
        return jsonify([])
    with open(DATA_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    return jsonify(rows)

@app.route("/force-scrape")
def force():
    try:
        scrape_data()
        return "⚡ force-scrape OK", 200
    except Exception as e:
        return f"❌ error: {e}", 500

@app.route("/export")
def export():
    return send_file(DATA_FILE, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
