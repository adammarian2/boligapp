from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import csv
import os
import scrape

app = Flask(__name__)

# przy starcie raz zbieramy dane
scrape.save_data()

# harmonogram codzienny o 6:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape.save_data, "cron", hour=6)
scheduler.start()

@app.route("/")
def index():
    selected = request.args.get("city", "Norge")
    # jeśli plik nie istnieje
    if not os.path.exists(scrape.DATA_PATH):
        return "Brak danych – poczekaj aż scraper zapisze pierwszy rekord."

    # wczytanie CSV
    rows = []
    with open(scrape.DATA_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["city"] == selected:
                rows.append(r)

    # przygotowanie list do Chart.js
    dates = [r["date"] for r in rows]
    finn = [int(r["finn"]) for r in rows]
    hjem = [int(r["hjem"]) for r in rows]
    total = [int(r["total"]) for r in rows]

    return render_template(
        "index.html",
        regions=list(scrape.FINN_REGIONS.keys()),
        selected_region=selected,
        dates=dates,
        finn_counts=finn,
        hjem_counts=hjem,
        total_counts=total
    )

@app.route("/data")
def data():
    return send_file(scrape.DATA_PATH, as_attachment=False)

@app.route("/export")
def export():
    return send_file(scrape.DATA_PATH, as_attachment=True)

@app.route("/force-scrape")
def force_scrape():
    try:
        scrape.save_data()
        return "⚡ Scraper uruchomiony poprawnie", 202
    except Exception as e:
        return f"❌ Błąd podczas scrape: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
