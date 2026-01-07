import pandas as pd
import unicodedata
import re

# --------- NORMALISATION TEXTE ---------
def normalize_text(s: str) -> str:
    """Normalise le texte : minuscules, suppression accents, espaces multiples."""
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r'\s+', ' ', s)
    return s

# --------- CHARGEMENT CSV ---------
def load_events(csv_file='data/csv_fusionne.csv'):
    """Charge le CSV et normalise les colonnes nécessaires."""
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"ERREUR: Le fichier '{csv_file}' est introuvable.")
        exit()

    required_cols = ['lat', 'lon', 'Category', 'City', 'Description', 'EventName']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print("ERREUR colonnes manquantes:", missing)
        exit()

    # Conversion numérique et nettoyage
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df.fillna('', inplace=True)

    # Gestion dates
    if "DateTime_start" in df.columns:
        df["DateTime_start"] = pd.to_datetime(df["DateTime_start"], errors="coerce")
    else:
        df["DateTime_start"] = pd.NaT

    # Normalisation catégories
    df["_cat_norm"] = df["Category"].astype(str).apply(normalize_text)
    return df

# --------- FILTRES ---------
def filter_by_category(df, interests_param):
    """
    Filtrage souple par catégorie :
    - Tolère plusieurs intérêts séparés par virgules
    - Tolère plusieurs catégories dans une cellule séparées par , ; / -
    - Tolère la casse, les accents et espaces
    """
    if not interests_param or "Category" not in df.columns:
        return df

    # Normalisation des intérêts
    interests = [normalize_text(i) for i in interests_param.split(',') if i.strip()]

    def category_match(cell):
        if pd.isna(cell):
            return False
        cell_norm = normalize_text(cell)
        # Découpe sur séparateurs fréquents
        tokens = [t.strip() for t in re.split(r'[;,/|-]', cell_norm) if t.strip()]
        # Match si un des intérêts est dans tokens ou dans la cellule entière
        return any(interest in tokens or interest in cell_norm for interest in interests)

    return df[df["Category"].apply(category_match)]

def filter_by_date(df, start, end):
    """Filtre les événements selon une plage de dates."""
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
