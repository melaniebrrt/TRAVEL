from flask import Blueprint, render_template, jsonify, request
from utils.data_utils import (
    load_events,
    filter_by_date,
    filter_by_category,
    normalize_text
)
import pandas as pd

# -------------------------------------------------
# TRADUCTION DES CATÉGORIES (AFFICHAGE)
# -------------------------------------------------
CATEGORY_TRANSLATIONS = {
    "concert": "Concerts",
    "concerts": "Concerts",
    "exhibition": "Expositions",
    "exhibitions": "Expositions",
    "market": "Marchés",
    "markets": "Marchés",
    "festival": "Festivals",
    "festivals": "Festivals",
    "theater": "Théâtre",
    "theatre": "Théâtre",
    "dance show": "Spectacles de danse",
    "dance shows": "Spectacles de danse",
    "opera": "Opéra",
    "musical": "Comédies musicales",
    "musicals": "Comédies musicales",
    "fair": "Foires",
    "fairs": "Foires",
    "flea market": "Brocantes",
    "flea markets": "Brocantes",
    "trade show": "Salons professionnels",
    "trade shows": "Salons professionnels",
    "christmas market": "Marchés de Noël",
    "christmas markets": "Marchés de Noël"
}

# -------------------------------------------------
# Blueprint principal
# -------------------------------------------------
bp = Blueprint("main", __name__)

# -------------------------------------------------
# FONCTION DE FILTRAGE COMMUNE
# -------------------------------------------------
def apply_filters(df, args):
    df = df.copy()

    interests = args.get("interests", "")
    query = normalize_text(args.get("q", ""))
    city = normalize_text(args.get("city", ""))
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")

    if interests:
        df = filter_by_category(df, interests)

    if city and "City" in df.columns:
        df = df[
            df["City"]
            .astype(str)
            .apply(normalize_text)
            .str.contains(city, na=False)
        ]

    if query:
        df = df[
            (
                df["EventName"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(query, na=False)
            )
            |
            (
                df["Description"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(query, na=False)
            )
        ]

    df = filter_by_date(df, start_date, end_date)
    return df

# -------------------------------------------------
# ROUTE FRONTEND
# -------------------------------------------------
@bp.route("/")
def index():
    return render_template("index.html")

# -------------------------------------------------
# API : catégories (TRADUITES)
# -------------------------------------------------
@bp.route("/api/categories")
def api_categories():
    df = load_events()
    if "Category" not in df.columns:
        return jsonify([])

    categories = (
        df["Category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    translated = {
        CATEGORY_TRANSLATIONS.get(normalize_text(cat), cat)
        for cat in categories
    }

    return jsonify(sorted(translated))

# -------------------------------------------------
# API : recherche intelligente
# -------------------------------------------------
@bp.route("/api/smart-search")
def smart_search():
    df = load_events()
    df = apply_filters(df, request.args)

    sort_param = request.args.get("sort", "")
    if sort_param == "date" and "DateTime_start" in df.columns:
        df = df.sort_values("DateTime_start", ascending=True)

    # Traduction des catégories (RÉSULTATS)
    if "Category" in df.columns:
        df["Category"] = df["Category"].apply(
            lambda c: CATEGORY_TRANSLATIONS.get(normalize_text(c), c)
            if isinstance(c, str) else c
        )

    # Nettoyage JSON
    df = df.where(pd.notna(df), None)

    # Limite affichage
    df = df.head(500)

    return jsonify(df.to_dict(orient="records"))

# -------------------------------------------------
# API : villes recommandées
# -------------------------------------------------
@bp.route("/api/cities-by-llm")
def cities_by_llm():
    df = load_events()
    df = apply_filters(df, request.args)

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
