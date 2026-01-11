from flask import Blueprint, render_template, jsonify, request
from utils.data_utils import (
    load_events,
    filter_by_date,
    filter_by_category,
    normalize_text
)
import pandas as pd

# -------------------------------------------------
# TRADUCTION DES CATÉGORIES (AFFICHAGE UNIQUEMENT)
# -------------------------------------------------
CATEGORY_TRANSLATIONS = {
    # --- Concerts ---
    "concert": "Concerts",
    "concerts": "Concerts",
    "konzerte": "Concerts",
    "conciertos": "Concerts",

    # --- Expositions ---
    "exhibition": "Expositions",
    "exhibitions": "Expositions",
    "ausstellungen": "Expositions",
    "exposiciones": "Expositions",

    # --- Marchés ---
    "market": "Marchés",
    "markets": "Marchés",
    "marches": "Marchés",
    "marchés": "Marchés",
    "märkte": "Marchés",
    "mercados": "Marchés",

    # --- Marchés aux puces ---
    "flea market": "Marchés aux puces",
    "flea markets": "Marchés aux puces",
    "flohmärkte": "Marchés aux puces",
    "mercadillos": "Marchés aux puces",

    # --- Marchés de Noël ---
    "christmas market": "Marchés de Noël",
    "christmas markets": "Marchés de Noël",
    "marches de noel": "Marchés de Noël",
    "marchés de noël": "Marchés de Noël",
    "weihnachtsmärkte": "Marchés de Noël",

    # --- Festivals / foires ---
    "festival": "Festivals",
    "festivals": "Festivals",
    "festivales": "Festivals",
    "ferias": "Fêtes et foires",
    "fetes et foires": "Fêtes et foires",

    # --- Salons professionnels ---
    "trade show": "Salons professionnels",
    "trade shows": "Salons professionnels",
    "fachmessen": "Salons professionnels",
    "ferias profesionales": "Salons professionnels",

    # --- Spectacles ---
    "dance": "Spectacles de danse",
    "danza": "Spectacles de danse",
    "tanzshows": "Spectacles de danse",

    # --- Théâtre ---
    "theatre": "Théâtre",
    "theater": "Théâtre",
    "teatro": "Théâtre",

    # --- Opéra ---
    "opera": "Opéra",
    "oper": "Opéra",

    # --- Comédies musicales ---
    "musical": "Comédies musicales",
    "musicals": "Comédies musicales",
    "musicales": "Comédies musicales",

    # --- Autres ---
    "ateliers": "Ateliers",
    "messen": "Messes",
}


# -------------------------------------------------
# OUTIL DE TRADUCTION ROBUSTE (ANTI-CRASH)
# -------------------------------------------------
def translate_category_safe(value):
    if not isinstance(value, str):
        return None
    key = normalize_text(value)
    return CATEGORY_TRANSLATIONS.get(key, value)

# -------------------------------------------------
# Blueprint principal
# -------------------------------------------------
bp = Blueprint("main", __name__)

# -------------------------------------------------
# FILTRAGE COMMUN
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
# FRONT
# -------------------------------------------------
@bp.route("/")
def index():
    return render_template("index.html")

# -------------------------------------------------
# API : CATEGORIES (TRADUITES)
# -------------------------------------------------
@bp.route("/api/categories")
def api_categories():
    df = load_events()
    if df.empty or "Category" not in df.columns:
        return jsonify([])

    translated = set()
    for c in df["Category"].dropna():
        if isinstance(c, str):
            translated.add(translate_category_safe(c))

    return jsonify(sorted(translated))

# -------------------------------------------------
# API : SMART SEARCH (STABLE)
# -------------------------------------------------
@bp.route("/api/smart-search")
def smart_search():
    df = load_events()
    if df.empty:
        return jsonify([])

    df = apply_filters(df, request.args)

    # Traduction catégories AVANT nettoyage
    if "Category" in df.columns:
        df["Category"] = df["Category"].apply(translate_category_safe)

    # Tri
    sort_param = request.args.get("sort", "")
    if sort_param == "date" and "DateTime_start" in df.columns:
        df = df.sort_values("DateTime_start", ascending=True)

    # Limite affichage (performance)
    df = df.head(500)

    # 🔥 NETTOYAGE FINAL JSON (ANTI NaN)
    df = df.astype(object)
    df = df.where(pd.notna(df), None)

    return jsonify(df.to_dict(orient="records"))

# -------------------------------------------------
# API : VILLES RECOMMANDÉES
# -------------------------------------------------
@bp.route("/api/cities-by-llm")
def cities_by_llm():
    df = load_events()
    if df.empty or "City" not in df.columns:
        return jsonify([])

    df = apply_filters(df, request.args)

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
