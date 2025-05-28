# app.py

from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import os
import traceback
import threading
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
    # wybór regionu z parametru GET ?city=
    selected = request.args.get("city", "Norge")
    # jeśli nie ma jeszcze pliku z danymi
    if not os.path.exists(scrape.DATA_PATH):
        return "Brak pliku data.csv – poczekaj na pierwszy scrape."

    # wczytanie CSV z pandas
    df = pd.read_csv(scrape.DATA_PATH, parse_dates=["date"])
    # filtr po wybranym regionie
    df = df[df["city"] == selected]
    # grupowanie po dacie i suma wartości
    grp = (
        df.groupby("date")[["finn", "hjem", "total"]]
          .sum()
          .reset_index()
          .sort_values("date")
    )

    dates        = grp["date"].dt.strftime("%Y-%m-%d").tolist()
    finn_counts  = grp["finn"].tolist()
    hjem_counts  = grp["hjem"].tolist()
    total_counts = grp["total"].tolist()

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
    # zwraca JSON (CSV jako plik statyczny)
    return send_file(scrape.DATA_PATH, as_attachment=False)

@app.route("/export")
def export():
    # pobieranie CSV
    return send_file(scrape.DATA_PATH, as_attachment=True)

@app.route("/force-scrape")
def force_scrape():
    # uruchamiamy scrape w tle, by nie blokować Gunicorna
    def _run():
        try:
            scrape.save_data()
            print("✅ Scrape zakończony pomyślnie")
        except Exception:
            print("❌ Błąd w scrape:\n", traceback.format_exc())

    threading.Thread(target=_run, daemon=True).start()
    return "🔄 Scrape ruszył w tle — sprawdź logi, gdy się zakończy.", 202

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
