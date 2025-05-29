from flask import Flask, render_template, jsonify, send_file, request
from apscheduler.schedulers.background import BackgroundScheduler
import os
import csv
import scrape

app = Flask(__name__)

# Przy starcie raz zebrane dane
try:
    scrape.save_data()
except Exception as e:
    print("Error initial scrape:", e)

# Każdego dnia o 06:00 dopisujemy nowy rekord
scheduler = BackgroundScheduler()
scheduler.add_job(scrape.save_data, 'cron', hour=6, minute=0)
scheduler.start()

@app.route('/')
def index():
    regions = list(scrape.REGION_CODES.keys())
    selected = request.args.get('city', 'Norge')
    return render_template('index.html',
        regions=regions,
        selected_region=selected
    )

@app.route('/data')
def data():
    if not os.path.exists(scrape.DATA_PATH):
        return jsonify([])
    with open(scrape.DATA_PATH, newline='', encoding='utf-8') as f:
        return jsonify(list(csv.DictReader(f)))

@app.route('/export')
def export():
    return send_file(scrape.DATA_PATH, as_attachment=True)

@app.route('/force-scrape')
def force_scrape():
    try:
        scrape.save_data()
        return "⚡ Scrape done", 200
    except Exception as e:
        return f"❌ Scrape error: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
