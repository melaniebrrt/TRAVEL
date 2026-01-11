import pandas as pd
import unicodedata
import re

# -------------------------------------------------
# NORMALISATION TEXTE
# -------------------------------------------------
def normalize_text(s: str) -> str:
    """
    Normalise le texte :
    - minuscules
    - suppression des accents
    - suppression des espaces multiples
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s


# -------------------------------------------------
# CHARGEMENT ET PRÉPARATION DU CSV
# -------------------------------------------------
def load_events(csv_file="data/csv_fusionne.csv"):
    """
    Charge le CSV et prépare les colonnes nécessaires
    sans jamais faire planter Flask.
    """
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"ERREUR : fichier '{csv_file}' introuvable.")
        return pd.DataFrame()

    required_cols = ["lat", "lon", "Category", "City", "Description", "EventName"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print("ERREUR : colonnes manquantes :", missing)
        return pd.DataFrame()

    # -------------------------------------------------
    # Coordonnées
    # -------------------------------------------------
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # -------------------------------------------------
    # Gestion des dates (POINT CRITIQUE)
    # -------------------------------------------------
    if "DateTime_start" in df.columns:
        df["DateTime_start"] = pd.to_datetime(
            df["DateTime_start"],
            errors="coerce",
            utc=True
        )
    else:
        df["DateTime_start"] = pd.NaT

    # 👉 Valeur sentinelle pour ne PAS exclure les événements futurs
    # Les événements sans date claire restent visibles
    df["DateTime_start"] = df["DateTime_start"].fillna(
        pd.Timestamp("2100-01-01", tz="UTC")
    )

    # -------------------------------------------------
    # Nettoyage colonnes texte
    # -------------------------------------------------
    text_cols = ["Category", "City", "Description", "EventName"]
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str)

    return df


# -------------------------------------------------
# FILTRAGE PAR CATÉGORIE
# -------------------------------------------------
def filter_by_category(df, interests_param):
    """
    Filtrage souple par catégorie :
    - plusieurs intérêts séparés par des virgules
    - catégories multiples dans une cellule
    - insensible à la casse / accents
    """
    if df.empty or not interests_param or "Category" not in df.columns:
        return df

    interests = [
        normalize_text(i)
        for i in interests_param.split(",")
        if i.strip()
    ]

    def category_match(cell):
        if not cell:
            return False
        cell_norm = normalize_text(cell)
        tokens = [
            t.strip()
            for t in re.split(r"[;,/|-]", cell_norm)
            if t.strip()
        ]
        return any(
            interest in tokens or interest in cell_norm
            for interest in interests
        )

    return df[df["Category"].apply(category_match)]


# -------------------------------------------------
# FILTRAGE PAR DATE
# -------------------------------------------------
def filter_by_date(df, start, end):
    """
    Filtre les événements selon une plage de dates.
    Les événements sans date réelle (sentinelle 2100)
    ne sont PAS exclus par défaut.
    """
    if df.empty or "DateTime_start" not in df.columns:
        return df

    if start:
        try:
            start = pd.to_datetime(start, utc=True)
            df = df[df["DateTime_start"] >= start]
        except Exception:
            pass

    if end:
        try:
            end = pd.to_datetime(end, utc=True)
            df = df[df["DateTime_start"] <= end]
        except Exception:
            pass

    return df

