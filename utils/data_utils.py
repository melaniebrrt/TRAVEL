import pandas as pd
import unicodedata
import re

# -------------------------------------------------
# NORMALISATION TEXTE
# -------------------------------------------------
def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s


# -------------------------------------------------
# PARSING ROBUSTE DES PLAGES DE DATES
# -------------------------------------------------
def parse_start_from_datetime(text):
    """
    Extrait la date de DÉBUT depuis un champ DateTime texte :
    - '6–10 may 2026'
    - '31 Dec 2025, 19:00 – 1 Jan 2026, 02:00'
    - '2. Jan. 2026, 23:00 – 3. Jan. 2026, 05:00'
    """
    if not isinstance(text, str) or not text.strip():
        return pd.NaT

    # On coupe sur les séparateurs de plage
    parts = re.split(r"[–\-—to]+", text)
    try:
        return pd.to_datetime(parts[0], errors="coerce", dayfirst=True)
    except:
        return pd.NaT


# -------------------------------------------------
# CHARGEMENT CSV
# -------------------------------------------------
def load_events(csv_file="data/csv_fusionne.csv"):
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"ERREUR : fichier '{csv_file}' introuvable.")
        return pd.DataFrame()

    # Colonnes obligatoires
    required_cols = ["Category", "City", "EventName", "Description"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    # Coordonnées
    df["lat"] = pd.to_numeric(df.get("lat"), errors="coerce")
    df["lon"] = pd.to_numeric(df.get("lon"), errors="coerce")

    # -------------------------------------------------
    # 🔥 RECONSTRUCTION DE LA DATE DE DÉBUT (CRUCIAL)
    # -------------------------------------------------
    df["DateTime_start"] = df["DateTime"].apply(parse_start_from_datetime)

    # Fallback : DateTime_end
    mask = df["DateTime_start"].isna() & df.get("DateTime_end").notna()
    df.loc[mask, "DateTime_start"] = pd.to_datetime(
        df.loc[mask, "DateTime_end"], errors="coerce"
    )

    # Fallback : année/mois/jour
    def fallback_year(row):
        year = row.get("Année_start") or row.get("Annee_start")
        if pd.notna(year):
            try:
                return pd.Timestamp(year=int(year), month=1, day=1)
            except:
                return pd.NaT
        return pd.NaT

    df["DateTime_start"] = df["DateTime_start"].fillna(
        df.apply(fallback_year, axis=1)
    )

    # -------------------------------------------------
    # Nettoyage texte
    # -------------------------------------------------
    for col in ["Category", "City", "EventName", "Description"]:
        df[col] = df[col].fillna("").astype(str)

    return df


# -------------------------------------------------
# FILTRES
# -------------------------------------------------
def filter_by_category(df, interests_param):
    if df.empty or not interests_param or "Category" not in df.columns:
        return df

    interests = [normalize_text(i) for i in interests_param.split(",") if i.strip()]

    def match(cell):
        cell_norm = normalize_text(cell)
        return any(i in cell_norm for i in interests)

    return df[df["Category"].apply(match)]


def filter_by_date(df, start, end):
    if df.empty or "DateTime_start" not in df.columns:
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
