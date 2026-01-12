from flask import Blueprint, render_template, jsonify, request
from utils.data_utils import (
    load_events,
    filter_by_date,
    filter_by_category,
    normalize_text
)
import pandas as pd
import re

CATEGORY_TRANSLATIONS = {
    "concert": "Concerts",
    "concerts": "Concerts",
    "konzerte": "Concerts",
    "conciertos": "Concerts",
    "exhibition": "Expositions",
    "exhibitions": "Expositions",
    "ausstellungen": "Expositions",
    "exposiciones": "Expositions",
    "market": "Marchés",
    "markets": "Marchés",
    "marches": "Marchés",
    "marchés": "Marchés",
    "märkte": "Marchés",
    "maerkte": "Marchés",
    "mercados": "Marchés",
    "flea market": "Marchés aux puces",
    "flea markets": "Marchés aux puces",
    "flohmärkte": "Marchés aux puces",
    "flohmaerkte": "Marchés aux puces",
    "mercadillos": "Marchés aux puces",
    "christmas market": "Marchés de Noël",
    "christmas markets": "Marchés de Noël",
    "marches de noel": "Marchés de Noël",
    "marchés de noël": "Marchés de Noël",
    "weihnachtsmärkte": "Marchés de Noël",
    "weihnachtsmaerkte": "Marchés de Noël",
    "festival": "Festivals",
    "festivals": "Festivals",
    "festivales": "Festivals",
    "ferias": "Fêtes et foires",
    "fetes et foires": "Fêtes et foires",
    "trade show": "Salons professionnels",
    "trade shows": "Salons professionnels",
    "fachmessen": "Salons professionnels",
    "ferias profesionales": "Salons professionnels",
    "dance": "Spectacles de danse",
    "danza": "Spectacles de danse",
    "tanzshows": "Spectacles de danse",
    "theatre": "Théâtre",
    "theater": "Théâtre",
    "teatro": "Théâtre",
    "opera": "Opéra",
    "oper": "Opéra",
    "musical": "Comédies musicales",
    "musicals": "Comédies musicales",
    "musicales": "Comédies musicales",
    "ateliers": "Ateliers",
    "messen": "Messes",
}

def translate_category_safe(value):
    if not isinstance(value, str) or not value.strip():
        return None

    norm = normalize_text(value)
    tokens = [
        t.strip()
        for t in re.split(r"[;,/|-]", norm)
        if t.strip()
    ]

    for token in tokens:
        if token in CATEGORY_TRANSLATIONS:
            return CATEGORY_TRANSLATIONS[token]

    return value


bp = Blueprint("main", __name__)


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
            .apply(normalize_text)
            .str.contains(city, na=False)
        ]

    if query:
        df = df[
            df["EventName"].apply(normalize_text).str.contains(query, na=False)
            |
            df["Description"].apply(normalize_text).str.contains(query, na=False)
        ]

    df = filter_by_date(df, start_date, end_date)
    return df


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/categories")
def api_categories():
    df = load_events()
    if df.empty or "Category" not in df.columns:
        return jsonify([])

    categories = set()
    for c in df["Category"]:
        translated = translate_category_safe(c)
        if translated:
            categories.add(translated)

    return jsonify(sorted(categories))


@bp.route("/api/smart-search")
def smart_search():
    df = load_events()
    if df.empty:
        return jsonify([])

    df = apply_filters(df, request.args)

    if "interest_score" in df.columns:
        df = df.sort_values("interest_score", ascending=False)

    if "Category" in df.columns:
        df["Category"] = df["Category"].apply(translate_category_safe)

    if request.args.get("sort") == "date":
        df = df.sort_values("DateTime_start", ascending=True)

    df = df.head(500)
    df = df.astype(object)
    df = df.where(pd.notna(df), None)

    return jsonify(df.to_dict(orient="records"))


@bp.route("/api/cities-by-llm")
def cities_by_llm():
    df = load_events()
    if df.empty or "City" not in df.columns:
        return jsonify([])

    df = apply_filters(df, request.args)

    df["City"] = df["City"].astype(str).str.strip()
    df = df[df["City"] != ""]

    city_counts = (
        df.groupby("City")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    return jsonify(city_counts.to_dict(orient="records"))
