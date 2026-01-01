from flask import Flask, jsonify, request, render_template
import pandas as pd
from flask_cors import CORS
import unicodedata
import re

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------
# 🔧 NORMALISATION TEXTE
# ---------------------------------------------------------
def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r'\s+', ' ', s)
    return s

# ---------------------------------------------------------
# 📥 CHARGEMENT CSV
# ---------------------------------------------------------
csv_file = 'csv_fusionne.csv'
try:
    df_events = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"ERREUR: Le fichier '{csv_file}' est introuvable.")
    exit()

# Colonnes essentielles
required_cols = ['lat', 'lon', 'Category', 'City', 'Description', 'EventName']
missing = [c for c in required_cols if c not in df_events.columns]
if missing:
    print("ERREUR colonnes manquantes:", missing)
    exit()

df_events['lat'] = pd.to_numeric(df_events['lat'], errors='coerce')
df_events['lon'] = pd.to_numeric(df_events['lon'], errors='coerce')
df_events.fillna('', inplace=True)

# Dates
if "DateTime_start" in df_events.columns:
    df_events["DateTime_start"] = pd.to_datetime(df_events["DateTime_start"], errors="coerce")
else:
    df_events["DateTime_start"] = pd.NaT

# Normalisation catégories
df_events["_cat_norm"] = df_events["Category"].apply(normalize_text)

# ---------------------------------------------------------
# 🧹 FILTRES
# ---------------------------------------------------------
def filter_by_category(df, interests_param):
    if not interests_param:
        return df
    interests = [normalize_text(i) for i in interests_param.split(',') if i.strip()]
    # ✅ Fix : comparaison exacte normalisée
    return df[df["_cat_norm"].isin(interests)]

def filter_by_date(df, start, end):
    if "DateTime_start" not in df.columns:
        return df
    if start:
        try:
            start = pd.to_datetime(start)
            df = df[df["DateTime_start"] >= start]
        except:
            pass
    if end:
        try:
            end = pd.to_datetime(end)
            df = df[df["DateTime_start"] <= end]
        except:
            pass
    return df

# ---------------------------------------------------------
# 🌐 ROUTE FRONT : page HTML principale
# ---------------------------------------------------------
@app.route('/')
def index():
    return render_template("index.html")

# ---------------------------------------------------------
# 📌 API : Liste des catégories
# ---------------------------------------------------------
@app.route('/api/categories')
def api_categories():
    categories = sorted(df_events["Category"].dropna().unique().tolist())
    return jsonify(categories)

# ---------------------------------------------------------
# 🔎 API : SMART SEARCH (recherche + filtres + tri)
# ---------------------------------------------------------
@app.route('/api/smart-search')
def smart_search():
    interests = request.args.get("interests", "").strip()
    query = request.args.get("q", "").strip().lower()
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    sort_param = request.args.get("sort", "")

    df_f = df_events.copy()
    df_f = filter_by_category(df_f, interests)
    df_f = filter_by_date(df_f, start_date, end_date)

    # recherche texte simple
    if query:
        df_f = df_f[
            df_f["EventName"].str.lower().str.contains(query, na=False) |
            df_f["Description"].str.lower().str.contains(query, na=False)
        ]

    if sort_param == "date" and "DateTime_start" in df_f.columns:
        df_f = df_f.sort_values("DateTime_start", ascending=True)

    df_f = df_f.reset_index(drop=True)
    return jsonify(df_f.to_dict("records"))

# ---------------------------------------------------------
# 🏙 API : Villes recommandées
# ---------------------------------------------------------
@app.route('/api/cities-by-llm')
def cities_by_llm():
    interests = request.args.get("interests", "").strip()
    query = request.args.get("q", "").strip().lower()
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    df_f = df_events.copy()
    df_f = filter_by_category(df_f, interests)
    df_f = filter_by_date(df_f, start_date, end_date)

    if query:
        df_f = df_f[
            df_f["EventName"].str.lower().str.contains(query, na=False) |
            df_f["Description"].str.lower().str.contains(query, na=False)
        ]

    df_f = df_f[df_f["City"].astype(str).str.strip() != ""]
    city_counts = (
        df_f.groupby("City", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )
    return jsonify(city_counts.to_dict("records"))

# ---------------------------------------------------------
# 🚀 LANCEMENT
# ---------------------------------------------------------
if __name__ == "__main__":
    print("Serveur OK ➜ http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

