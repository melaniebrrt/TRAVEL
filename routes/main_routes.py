from flask import Blueprint, render_template, jsonify, request
from utils.data_utils import (
    load_events,
    filter_by_date,
    filter_by_category,
    normalize_text
)
import pandas as pd

# -------------------------------------------------
# Blueprint principal
# -------------------------------------------------
bp = Blueprint("main", __name__)

# -------------------------------------------------
# Chargement des données (1 seule fois)
# -------------------------------------------------
df_events = load_events()

# -------------------------------------------------
# FONCTION DE FILTRAGE COMMUNE
# -------------------------------------------------
def apply_filters(df, args):
    """
    Applique les filtres communs :
    - intérêts / catégorie
    - recherche texte
    - dates
    """
    df = df.copy()

    # ---------- Paramètres ----------
    interests = args.get("interests", "")
    query = normalize_text(args.get("q", ""))
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")

    # ---------- Filtre catégorie (robuste) ----------
    if interests:
        df = filter_by_category(df, interests)

    # ---------- Recherche texte ----------
    if query:
        df = df[
            df["EventName"]
            .astype(str)
            .apply(normalize_text)
            .str.contains(query, na=False)
            |
            df["Description"]
            .astype(str)
            .apply(normalize_text)
            .str.contains(query, na=False)
        ]

    # ---------- Filtre dates ----------
    df = filter_by_date(df, start_date, end_date)

    return df

# -------------------------------------------------
# ROUTE FRONTEND
# -------------------------------------------------
@bp.route("/")
def index():
    return render_template("index.html")

# -------------------------------------------------
# API : catégories
# -------------------------------------------------
@bp.route("/api/categories")
def api_categories():
    categories = (
        df_events["Category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    return jsonify(sorted(categories))

# -------------------------------------------------
# API : recherche intelligente
# -------------------------------------------------
@bp.route("/api/smart-search")
def smart_search():
    sort_param = request.args.get("sort", "")
    df = apply_filters(df_events, request.args)

    # Tri par date si demandé
    if sort_param == "date" and "DateTime_start" in df.columns:
        df = df.sort_values("DateTime_start", ascending=True)

    # Sérialisation des dates
    if "DateTime_start" in df.columns:
        df["DateTime_start"] = (
            df["DateTime_start"]
            .where(df["DateTime_start"].notna(), None)
            .astype(str)
        )

    return jsonify(df.to_dict(orient="records"))

# -------------------------------------------------
# API : villes recommandées
# -------------------------------------------------
@bp.route("/api/cities-by-llm")
def cities_by_llm():
    df = apply_filters(df_events, request.args)

    if "City" not in df.columns:
        return jsonify([])

    df["City"] = df["City"].astype(str).str.strip()
    df = df[df["City"] != ""]

    if df.empty:
        return jsonify([])

    city_counts = (
        df.groupby("City")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    return jsonify(city_counts.to_dict(orient="records"))
