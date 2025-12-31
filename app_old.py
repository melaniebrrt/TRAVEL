from flask import Flask, jsonify, request, render_template
import pandas as pd
from flask_cors import CORS
import unicodedata
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
# from sentence_transformers import SentenceTransformer, util  # Ancien code Torch

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
csv_file = 'df_final_trad.csv'
try:
    df_events = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"ERREUR: Le fichier '{csv_file}' est introuvable.")
    exit()

# Vérification colonnes essentielles
required_cols = ['lat', 'lon', 'Category', 'City', 'Description', 'EventName']
missing = [c for c in required_cols if c not in df_events.columns]
if missing:
    print("ERREUR colonnes manquantes:", missing)
    exit()

# Nettoyage lat/lon
df_events['lat'] = pd.to_numeric(df_events['lat'], errors='coerce')
df_events['lon'] = pd.to_numeric(df_events['lon'], errors='coerce')
df_events.fillna('', inplace=True)

# ---------------------------------------------------------
# 📅 CONVERSION DES DATES
# ---------------------------------------------------------
if "DateTime_start" in df_events.columns:
    df_events["DateTime_start"] = pd.to_datetime(df_events["DateTime_start"], errors="coerce")
else:
    df_events["DateTime_start"] = pd.NaT

# ---------------------------------------------------------
# 🗂 NORMALISATION CATÉGORIES
# ---------------------------------------------------------
df_events["_cat_norm"] = df_events["Category"].apply(normalize_text)

# ---------------------------------------------------------
# 🤖 CHARGEMENT DES EMBEDDINGS PRÉ-CALCULÉS
# ---------------------------------------------------------
# Ancien code avec modèle Torch :
# model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
# event_embeddings = model.encode(df_events['EventName'].fillna('') + ' ' + df_events['Description'].fillna(''),
#                                 convert_to_tensor=True)

# Nouveau code pour Render gratuit : embeddings pré-calculés en numpy
try:
    event_embeddings = np.load("event_embeddings.npy")
except FileNotFoundError:
    print("ERREUR: Le fichier 'event_embeddings.npy' est introuvable. Veuillez le générer localement.")
    exit()

# ---------------------------------------------------------
# 🧹 FILTRES
# ---------------------------------------------------------
def filter_by_category(df, interests_param):
    if not interests_param:
        return df
    interests = [normalize_text(i) for i in interests_param.split(',') if i.strip()]
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
    interests = request.args.get("interests", "")
    query = request.args.get("q", "").strip()
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    sort_param = request.args.get("sort", "")

    df_f = filter_by_category(df_events, interests)
    df_f = filter_by_date(df_f, start_date, end_date)

    if query:
        # q_emb = model.encode(query, convert_to_tensor=True)  # ancien code Torch
        # filt_emb = event_embeddings[df_f.index.tolist()]
        # scores = util.cos_sim(q_emb, filt_emb)[0].cpu().numpy()
        q_emb = np.load("query_embedding.npy") if False else np.random.rand(event_embeddings.shape[1])  # placeholder
        filt_emb = event_embeddings[df_f.index.tolist()]
        scores = cosine_similarity([q_emb], filt_emb)[0]
        df_f = df_f.iloc[np.argsort(-scores)]

    if sort_param == "date" and "DateTime_start" in df_f.columns:
        df_f = df_f.sort_values("DateTime_start", ascending=True)

    return jsonify(df_f.to_dict("records"))

# ---------------------------------------------------------
# 🏙 API : Villes recommandées
# ---------------------------------------------------------
@app.route('/api/cities-by-llm')
def cities_by_llm():
    interests = request.args.get("interests", "")
    query = request.args.get("q", "").strip()
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    df_f = filter_by_category(df_events, interests)
    df_f = filter_by_date(df_f, start_date, end_date)
    df_f = df_f[df_f["City"].astype(str).str.strip() != ""]

    if query:
        # Ancien code Torch
        # q_emb = model.encode(query, convert_to_tensor=True)
        # filt_emb = event_embeddings[df_f.index.tolist()]
        # scores = util.cos_sim(q_emb, filt_emb)[0].cpu().numpy()
        q_emb = np.random.rand(event_embeddings.shape[1])  # placeholder
        filt_emb = event_embeddings[df_f.index.tolist()]
        scores = cosine_similarity([q_emb], filt_emb)[0]
        df_f = df_f.iloc[np.argsort(-scores)]

    city_counts = (
        df_f.groupby("City", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("count", ascending=False)
    )
    return jsonify(city_counts.to_dict("records"))

# ---------------------------------------------------------
# 📍 API : Événements par ville
# ---------------------------------------------------------
@app.route('/api/events-by-city')
def events_by_city():
    city = request.args.get("city", "").strip()
    interests = request.args.get("interests", "")
    query = request.args.get("q", "").strip()
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    sort_param = request.args.get("sort", "")

    if not city:
        return jsonify({"error": "Paramètre city manquant"}), 400

    df_f = df_events[df_events["City"].astype(str).str.lower().str.strip() == city.lower()]
    df_f = filter_by_category(df_f, interests)
    df_f = filter_by_date(df_f, start_date, end_date)

    if query:
        # Ancien code Torch
        # q_emb = model.encode(query, convert_to_tensor=True)
        # filt_emb = event_embeddings[df_f.index.tolist()]
        # scores = util.cos_sim(q_emb, filt_emb)[0].cpu().numpy()
        q_emb = np.random.rand(event_embeddings.shape[1])  # placeholder
        filt_emb = event_embeddings[df_f.index.tolist()]
        scores = cosine_similarity([q_emb], filt_emb)[0]
        df_f = df_f.iloc[np.argsort(-scores)]

    if sort_param == "date" and "DateTime_start" in df_f.columns:
        df_f = df_f.sort_values("DateTime_start", ascending=True)

    return jsonify(df_f.to_dict("records"))

# ---------------------------------------------------------
# 🚀 LANCEMENT
# ---------------------------------------------------------
if __name__ == "__main__":
    print("Serveur OK ➜ http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

