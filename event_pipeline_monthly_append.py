import subprocess
import sys
import os

# --- 🛠️ AUTO-RÉPARATION : INSTALLATION DES DÉPENDANCES ---
def install(package):
    print(f"🔧 Installation automatique de : {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import pandas
except ImportError:
    install("pandas")

try:
    import googletrans
except ImportError:
    install("googletrans==4.0.0rc1")

try:
    from serpapi import GoogleSearch
except ImportError:
    install("google-search-results")
    from serpapi import GoogleSearch  # On réessaie l'import après installation

try:
    from geopy.geocoders import Nominatim
except ImportError:
    install("geopy")
# -------------------------------------------------------

import csv
from dateutil.parser import parse
import time
import json
import random

# ... LE RESTE DE TON CODE RESTE PAREIL EN DESSOUS ...

from serpapi import GoogleSearch
import os
import csv
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from googletrans import Translator
import time
import json
import random

# -------------------------------
# CONFIGURATION
# -------------------------------
API_KEY = os.getenv("SERPAPI_API_KEY")

if not API_KEY:
    # Pour tester en local sans variable d'env, décommente la ligne suivante :
    # API_KEY = "TA_CLE_API_ICI"
    pass

if not API_KEY or API_KEY == "TA_CLE_API_ICI":
    raise ValueError("❌ Erreur : La clé SERPAPI_API_KEY est manquante.")

MAX_EVENTS = 5          
TYPES_PER_CITY = 9      

# Villes
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

# Types d'événements
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
# Ajout de fallbacks simples si une langue manque
if "it" not in event_types_by_lang: event_types_by_lang["it"] = event_types_by_lang["en"]

# -------------------------------
# INIT ET UTILITAIRES
# -------------------------------
# Création du dossier data s'il n'existe pas (CRUCIAL)
os.makedirs("data", exist_ok=True)

translator = Translator()
geolocator = Nominatim(user_agent="event_scraper_monthly_bot_v1")
geo_cache_file = "data/geo_cache.json"
output_file = "data/events_monthly.csv"

# Charger cache géoloc
if os.path.exists(geo_cache_file):
    with open(geo_cache_file, "r", encoding="utf-8") as f:
        try:
            geo_cache = json.load(f)
        except json.JSONDecodeError:
            geo_cache = {}
else:
    geo_cache = {}

# Charger CSV existant
existing_links = set()
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "Link" in row:
                existing_links.add(row["Link"])

def save_geo_cache():
    with open(geo_cache_file, "w", encoding="utf-8") as f:
        json.dump(geo_cache, f, ensure_ascii=False, indent=2)

def translate_fr(text):
    """Traduction robuste : retourne le texte original si Google échoue"""
    if not text:
        return ""
    try:
        # Petit délai aléatoire pour éviter le ban IP Google
        time.sleep(random.uniform(0.1, 0.5)) 
        return translator.translate(text, src='auto', dest='fr').text
    except Exception as e:
        print(f"⚠️ Traduction échouée pour '{text[:15]}...': {e}")
        return text # Fallback sur l'original

def geolocate(address):
    if not address:
        return None, None
    if address in geo_cache:
        return geo_cache[address]
    try:
        time.sleep(1.5) # Nominatim demande 1 req/sec max
        location = geolocator.geocode(address, timeout=10)
        if location:
            latlon = (location.latitude, location.longitude)
            geo_cache[address] = latlon
            save_geo_cache()
            return latlon
    except Exception as e:
        print(f"⚠️ Erreur géoloc: {e}")
    
    geo_cache[address] = (None, None)
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
print("🚀 Démarrage du scraper...")

file_exists = os.path.exists(output_file)

# On ouvre en mode 'a' (append)
with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    
    # Si le fichier est vide ou nouveau, on écrit l'en-tête
    if not file_exists or os.path.getsize(output_file) == 0:
        writer.writerow([
            "Source","Category","EventName","DateTime","City","VenueName","Address","Link","Description",
            "DateTime_start","DateTime_end","Jour_start","Mois_start","Annee_start","Heure_start","Heure_end",
            "lat","lon","duration_h","tags"
        ])

    for ville in villes:
        lang_key = ville.get("hl", "en")
        types = event_types_by_lang.get(lang_key, event_types_by_lang["en"])[:TYPES_PER_CITY]

        for event_type in types:
            query = f"{event_type} in {ville['name']}"
            print(f"🔍 {ville['name']}: {event_type}")

            params = {
                "engine": "google_events",
                "api_key": API_KEY,
                "q": query,
                "location": ville["location"],
                "gl": ville["gl"],
                "hl": ville["hl"],
            }

            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                events = results.get("events_results", [])[:MAX_EVENTS]
            except Exception as e:
                print(f"❌ Erreur SerpApi pour {query}: {e}")
                continue

            count_new = 0
            for ev in events:
                link = ev.get("link", "")
                if link in existing_links:
                    continue
                
                existing_links.add(link)
                
                # Extraction
                title_orig = ev.get("title", "")
                desc_orig = ev.get("description", "")
                venue_list = ev.get("address", [])
                venue_name = ", ".join(venue_list) if isinstance(venue_list, list) else venue_list
                date_str = ev.get("date", {}).get("when", "")
                
                # Traitement
                title = translate_fr(title_orig)
                description = translate_fr(desc_orig)
                # On ne traduit pas le nom du lieu pour aider la géoloc
                category_fr = translate_fr(event_type)
                
                dt_start, dt_end, duration_h = parse_date_range(date_str)
                lat, lon = geolocate(venue_name)

                row = [
                    "SerpApi", category_fr, title, date_str, ville["name"],
                    venue_name, venue_name, link, description,
                    dt_start.isoformat() if dt_start else "",
                    dt_end.isoformat() if dt_end else "",
                    dt_start.day if dt_start else "",
                    dt_start.month if dt_start else "",
                    dt_start.year if dt_start else "",
                    dt_start.hour if dt_start else "",
                    dt_end.hour if dt_end else "",
                    lat, lon,
                    round(duration_h,2) if duration_h else "",
                    category_fr
                ]
                
                writer.writerow(row)
                count_new += 1
                # Flush pour écrire physiquement sur le disque immédiatement
                csvfile.flush() 
            
            if count_new > 0:
                print(f"   ✅ {count_new} nouveaux événements ajoutés.")

print(f"\n🎯 Terminé. Données sauvegardées dans {output_file}")
