from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd, os
import scrape

app = Flask(__name__)

# pierwsze pobranie
try:
    scrape.save_data()
except Exception as e:
    print("Initial scrape failed:", e)

# harmonogram 6:00
sched = BackgroundScheduler()
sched.add_job(scrape.save_data, "cron", hour=6, minute=0)
sched.start()

@app.route("/")
def index():
    city = request.args.get("city", "Norge")
    if not os.path.exists(scrape.DATA_PATH):
        return "Poczekaj na pierwsze zbieranie danych..."
    df = pd.read_csv(scrape.DATA_PATH, parse_dates=["date"])
    df = df[df["city"] == city]
    grp = df.groupby("date")[["finn","hjem","total"]].sum().reset_index().sort_values("date")
    dates       = grp["date"].dt.strftime("%Y-%m-%d").tolist()
    finn_counts = grp["finn"].tolist()
    hjem_counts = grp["hjem"].tolist()
    total_counts= grp["total"].tolist()
    return render_template("index.html",
        regions=list(scrape.FINN_REGIONS.keys()),
        selected=city,
        dates=dates,
        finn_counts=finn_counts,
        hjem_counts=hjem_counts,
        total_counts=total_counts
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
        return "OK", 200
    except Exception as e:
        return f"ERROR: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
