from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import os
import scrape

app = Flask(__name__)

# on start scrape
scrape.save_data()

# schedule daily at 06:00
sched = BackgroundScheduler()
sched.add_job(scrape.save_data, "cron", hour=6, minute=0)
sched.start()

@app.route("/")
def index():
    region = request.args.get("city", "Norge")
    if not os.path.exists(scrape.DATA_PATH):
        return "Waiting for first scrape..."
    df = pd.read_csv(scrape.DATA_PATH, parse_dates=["date"])
    df = df[df["city"] == region].sort_values("date")
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    finn_counts = df["finn"].tolist()
    hjem_counts = df["hjem"].tolist()
    total_counts = df["total"].tolist()
    return render_template(
        "index.html",
        regions=list(scrape.REGION_CODES.keys()),
        selected_region=region,
        dates=dates,
        finn_counts=finn_counts,
        hjem_counts=hjem_counts,
        total_counts=total_counts
    )

@app.route("/data")
def data():
    return send_file(scrape.DATA_PATH)

@app.route("/force-scrape")
def force_scrape():
    try:
        scrape.save_data()
        return "⏱️ scrape triggered", 202
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
