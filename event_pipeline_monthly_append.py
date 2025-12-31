from serpapi import GoogleSearch
import os
import csv
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from googletrans import Translator
import time
import json

# -------------------------------
# CONFIGURATION POUR 150 REQUÊTES MAX
# -------------------------------
API_KEY = os.getenv("SERPAPI_API_KEY") or "TA_CLE_API_ICI"
if API_KEY == "TA_CLE_API_ICI":
    raise ValueError("❌ Remplace TA_CLE_API_ICI par ta clé API ou définis SERPAPI_API_KEY.")

MAX_EVENTS = 5          # max événements par type
TYPES_PER_CITY = 9      # 16 villes x 9 types = 144 requêtes max

# Villes (Londres inclus)
villes = [
    {"name": "London", "location": "London, United Kingdom", "gl": "uk", "hl": "en"},
    {"name": "Berlin", "location": "Berlin, Germany", "gl": "de", "hl": "de"},
    {"name": "Paris", "location": "Paris, France", "gl": "fr", "hl": "fr"},
    {"name": "Rome", "location": "Rome, Italy", "gl": "it", "hl": "it"},
    {"name": "Madrid", "location": "Madrid, Spain", "gl": "es", "hl": "es"},
    {"name":"Amsterdam", "location":"Amsterdam, Netherlands", "gl":"nl", "hl":"nl"},
    {"name":"Bruxelles", "location":"Brussels, Belgium", "gl":"be", "hl":"fr"},
    {"name":"Vienne", "location":"Vienna, Austria", "gl":"at", "hl":"de"},
    {"name":"Zurich", "location":"Zurich, Switzerland", "gl":"ch", "hl":"de"},
    {"name":"Genève", "location":"Geneva, Switzerland", "gl":"ch", "hl":"fr"},
    {"name":"Barcelone", "location":"Barcelona, Spain", "gl":"es", "hl":"es"},
    {"name":"Lisbonne", "location":"Lisbon, Portugal", "gl":"pt", "hl":"pt"},
    {"name":"Stockholm", "location":"Stockholm, Sweden", "gl":"se", "hl":"sv"},
    {"name":"Copenhague", "location":"Copenhagen, Denmark", "gl":"dk", "hl":"da"},
    {"name":"Oslo", "location":"Oslo, Norway", "gl":"no", "hl":"no"},
    {"name":"Dublin", "location":"Dublin, Ireland", "gl":"ie", "hl":"en"},
]

# Types d'événements par langue (9 max)
event_types_by_lang = {
    "fr": ["concerts","expositions","marchés","festivals","théâtre","spectacles de danse",
           "opéra","comédies musicales","foires"],
    "en": ["concerts","exhibitions","markets","festivals","theater","dance shows",
           "opera","musicals","fairs"],
    "de": ["konzerte","ausstellungen","märkte","festivals","theater","tanzshows",
           "oper","musicals","messen"],
    "it": ["concerti","mostre","mercati","festival","teatro","spettacoli di danza",
           "opera","musical","fiere"],
    "es": ["conciertos","exposiciones","mercados","festivales","teatro","espectáculos de danza",
           "ópera","musicales","ferias"],
    "nl": ["concerten","tentoonstellingen","markten","festivals","theater","dansvoorstellingen",
           "opera","musicals","beurzen"],
    "pt": ["concertos","exposições","mercados","festivais","teatro","espetáculos de dança",
           "ópera","musicais","feiras"],
    "sv": ["konserter","utställningar","marknader","festivaler","teater","dansföreställningar",
           "opera","musikaler","mässor"],
    "da": ["koncerter","udstillinger","markeder","festivaler","teater","danseshows",
           "opera","musicals","messer"],
    "no": ["konserter","utstillinger","markeder","festivaler","teater","danseshow",
           "opera","musikaler","messer"],
    "ie": ["concerts","exhibitions","markets","festivals","theater","dance shows",
           "opera","musicals","fairs"]
}

# -------------------------------
# INIT
# -------------------------------
translator = Translator()
geolocator = Nominatim(user_agent="event_scraper_monthly_append")
geo_cache_file = "data/geo_cache.json"
output_file = "data/events_monthly.csv"

# Charger cache géoloc
try:
    with open(geo_cache_file, "r", encoding="utf-8") as f:
        geo_cache = json.load(f)
except:
    geo_cache = {}

# Charger CSV existant pour éviter duplicats
existing_links = set()
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_links.add(row["Link"])

def save_geo_cache():
    with open(geo_cache_file, "w", encoding="utf-8") as f:
        json.dump(geo_cache, f, ensure_ascii=False, indent=2)

def translate_fr(text):
    if not text:
        return ""
    try:
        return translator.translate(text, src='auto', dest='fr').text
    except:
        return text

def geolocate(address):
    if not address:
        return None, None
    if address in geo_cache:
        return geo_cache[address]
    try:
        location = geolocator.geocode(address)
        if location:
            latlon = (location.latitude, location.longitude)
            geo_cache[address] = latlon
            save_geo_cache()
            return latlon
    except:
        pass
    geo_cache[address] = (None, None)
    save_geo_cache()
    return None, None

def parse_date_range(date_str):
    if not date_str:
        return None, None, None
    try:
        parts = date_str.split("–")
        dt_start = parse(parts[0].strip(), fuzzy=True)
        dt_end = parse(parts[1].strip(), fuzzy=True) if len(parts) > 1 else None
        duration_h = (dt_end - dt_start).total_seconds()/3600 if dt_end else None
        return dt_start, dt_end, duration_h
    except:
        return None, None, None

# -------------------------------
# SCRIPT PRINCIPAL
# -------------------------------
file_exists = os.path.exists(output_file)
with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    if not file_exists or os.path.getsize(output_file) == 0:
        # Ajouter en-tête si CSV vide ou inexistant
        writer.writerow([
            "Source","Category","EventName","DateTime","City","VenueName","Address","Link","Description",
            "DateTime_start","DateTime_end","Jour_start","Mois_start","Annee_start","Heure_start","Heure_end",
            "lat","lon","duration_h","tags"
        ])

    for ville in villes:
        types = event_types_by_lang.get(ville["hl"], ["concerts"])[:TYPES_PER_CITY]

        for event_type in types:
            query = f"{event_type} in {ville['name']}"
            print(f"\n🔍 Recherche: '{event_type}' à {ville['name']}")

            params = {
                "engine": "google_events",
                "api_key": API_KEY,
                "q": query,
                "location": ville["location"],
                "gl": ville["gl"],
                "hl": ville["hl"],
                "start": 0
            }

            try:
                search = GoogleSearch(params)
                results = search.get_dict()
            except Exception as e:
                print(f"❌ Erreur SerpApi: {e}")
                continue

            events = results.get("events_results", [])[:MAX_EVENTS]
            if not events:
                continue

            for ev in events:
                link = ev.get("link", "")
                if link in existing_links:
                    continue  # déjà présent
                existing_links.add(link)

                title = translate_fr(ev.get("title", ""))
                description = translate_fr(ev.get("description", ""))
                venue_name = translate_fr(", ".join(ev.get("address", [])))
                category_fr = translate_fr(event_type)
                city = ville["name"]
                date_str = ev.get("date", {}).get("when", "")

                dt_start, dt_end, duration_h = parse_date_range(date_str)
                lat, lon = geolocate(venue_name)
                time.sleep(1)  # pause Nominatim

                writer.writerow([
                    "SerpApi",
                    category_fr,
                    title,
                    date_str,
                    city,
                    venue_name,
                    venue_name,
                    link,
                    description,
                    dt_start.isoformat() if dt_start else "",
                    dt_end.isoformat() if dt_end else "",
                    dt_start.day if dt_start else "",
                    dt_start.month if dt_start else "",
                    dt_start.year if dt_start else "",
                    dt_start.hour if dt_start else "",
                    dt_end.hour if dt_end else "",
                    lat,
                    lon,
                    round(duration_h,2) if duration_h else "",
                    category_fr
                ])

print(f"\n🎯 Pipeline terminé. '{output_file}' mis à jour avec les nouveaux événements.")
