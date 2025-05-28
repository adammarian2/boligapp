# app.py

from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import os
import traceback
import scrape

app = Flask(__name__)

# Pierwsze uruchomienie scraper’a przy starcie
scrape.save_data()

# Harmonogram: codziennie o 06:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape.save_data, "cron", hour=6)
scheduler.start()

@app.route("/")
def index():
    selected = request.args.get("city", "Norge")
    if not os.path.exists(scrape.DATA_PATH):
        return "Brak pliku data.csv – poczekaj na pierwszy scrape."

    # Wczytujemy CSV, filtrujemy po regionie, grupujemy i sortujemy
    df = pd.read_csv(scrape.DATA_PATH, parse_dates=["date"])
    df = df[df["city"] == selected]
    grp = (
        df.groupby("date")[["finn", "hjem", "total"]]
          .sum()
          .reset_index()
          .sort_values("date")
    )

    dates       = grp["date"].dt.strftime("%Y-%m-%d").tolist()
    finn_counts = grp["finn"].tolist()
    hjem_counts = grp["hjem"].tolist()
    total_counts= grp["total"].tolist()

    return render_template(
        "index.html",
        dates=dates,
        finn_counts=finn_counts,
        hjem_counts=hjem_counts,
        total_counts=total_counts,
        regions=list(scrape.REGION_CODES.keys()),
        selected_region=selected
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
        return "⚡ Scrape uruchomiony poprawnie", 200
    except Exception as e:
        tb = traceback.format_exc()
        return f"❌ Błąd podczas scrape:\n{e}\n\n{tb}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
