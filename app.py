from flask import Flask, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import scrape
import traceback

app = Flask(__name__)

# pierwszy scrape przy starcie
try:
    scrape.save_data()
except Exception as e:
    print("Error initial scrape:", e)

# harmonogram codziennie o 6:00
scheduler = BackgroundScheduler()
scheduler.add_job(scrape.save_data, "cron", hour=6, minute=0)
scheduler.start()

@app.route("/", methods=["GET"])
def index():
    selected = request.args.get("region", "Norge")
    # wczytanie CSV
    import pandas as pd
    df = pd.read_csv(scrape.DATA_PATH, parse_dates=["date"])
    # filtrowanie po regionie
    df = df[df["city"] == selected]
    # grupowanie po dacie
    grp = (
        df.groupby("date")[["finn","hjem","total"]]
          .sum()
          .reset_index()
          .sort_values("date")
    )
    dates        = grp["date"].dt.strftime("%Y-%m-%d").tolist()
    finn_counts  = grp["finn"].tolist()
    hjem_counts  = grp["hjem"].tolist()
    total_counts = grp["total"].tolist()

    return render_template("index.html",
        regions=list(scrape.REGION_CODES.keys()),
        selected_region=selected,
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
def force():
    try:
        scrape.save_data()
        return "✅ Scrape uruchomiony", 202
    except Exception as e:
        tb = traceback.format_exc()
        return f"❌ Błąd during scrape:\n{e}\n\n{tb}", 500

if __name__=="__main__":
    app.run(host="0.0.0.0", port=10000)
