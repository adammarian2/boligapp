import requests
from bs4 import BeautifulSoup
import re
import datetime
import csv
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Regiony i kody FINN oraz slugi Hjem
REGION_CODES = {
    'Norge': None,
    'Oslo': '0.20061',
    'Agder': '0.22042',
    'Akershus': '0.20003',
    'Møre og Romsdal': '0.20015',
    'Trøndelag': '0.20016'
}

CATEGORY_CODES = {
    'leiligheter': ('1', 'leilighet'),
    'eneboliger':  ('2', 'enebolig'),
    'tomter':      ('3', 'tomt'),
}

DATA_PATH = 'data.csv'
FIELDS = ['date', 'city', 'category', 'finn', 'hjem', 'total']

def scrape_finn(region_code, category_code):
    url = f'https://www.finn.no/realestate/homes/search.html?property_type={category_code}'
    if region_code:
        url += f'&location={region_code}'
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    meta = soup.find('meta', attrs={'name': 'description'})
    content = meta and meta.get('content', '') or ''
    # Szukamy "123 456 bolig" – to złapiemy liczbę
    m = re.search(r'([\d\u00A0 ]+)\s+bolig', content, re.IGNORECASE)
    if not m:
        return 0
    num_str = m.group(1).replace('\u00A0','').replace(' ','')
    return int(num_str)

def scrape_hjem(region, category_slug):
    if region == 'Norge':
        url = f'https://hjem.no/kjop/{category_slug}'
    else:
        slug = region.lower().replace(' ', '-')
        url = f'https://hjem.no/kjop/{slug}/{category_slug}'
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    text = r.text
    # Szukamy "123 456 resultater"
    m = re.search(r'([\d\u00A0 ]+)\s+result', text, re.IGNORECASE)
    if not m:
        return 0
    num_str = m.group(1).replace('\u00A0','').replace(' ','')
    return int(num_str)

def save_data():
    today = datetime.date.today().isoformat()
    write_header = not os.path.exists(DATA_PATH)
    with open(DATA_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        for city, region_code in REGION_CODES.items():
            for category, (finn_code, hjem_slug) in CATEGORY_CODES.items():
                fcnt = scrape_finn(region_code, finn_code)
                hcnt = scrape_hjem(city, hjem_slug)
                writer.writerow({
                    'date': today,
                    'city': city,
                    'category': category,
                    'finn': fcnt,
                    'hjem': hcnt,
                    'total': fcnt + hcnt
                })
