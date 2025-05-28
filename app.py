from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import csv, os
import scrape

app = Flask(__name__)

# pierwszy scrape przy starcie
scrape.scrape_data()

# harmonogram codziennie o 06:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape.scrape_data, "cron", hour=6, minute=0)
scheduler.start()

@app.route("/")
def index():
    selected = request.args.get("city", "Norge")

    if not os.path.exists(scrape.DATA_PATH):
        return "Brak pliku data.csv – poczekaj na pierwszy scrape."

    rows = []
    with open(scrape.DATA_PATH, newline="") as f:
        for r in csv.DictReader(f):
            if r["city"] == selected:
                rows.append(r)

    # sortowanie
    rows.sort(key=lambda r: r["date"])
    dates = [r["date"] for r in rows]
    counts = [int(r["finn"]) for r in rows]

    return render_template(
        "index.html",
        regions=list(scrape.REGION_CODES.keys()),
        selected_region=selected,
        dates=dates,
        counts=counts
    )

@app.route("/data")
def data():
    return send_file(scrape.DATA_PATH, mimetype="text/csv")

@app.route("/export")
def export():
    return send_file(scrape.DATA_PATH, as_attachment=True)

@app.route("/force-scrape")
def force_scrape():
    try:
        scrape.scrape_data()
        return "⚡ Scrape FINN wykonany pomyślnie", 200
    except Exception as e:
        import traceback
        return f"❌ Błąd podczas scrape:\n{e}\n\n{traceback.format_exc()}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
