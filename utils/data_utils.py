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
    if not isinstance(text, str) or not text.strip():
        return pd.NaT

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

    required_cols = ["Category", "City", "EventName", "Description"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    df["lat"] = pd.to_numeric(df.get("lat"), errors="coerce")
    df["lon"] = pd.to_numeric(df.get("lon"), errors="coerce")

    df["DateTime_start"] = df["DateTime"].apply(parse_start_from_datetime)

    mask = df["DateTime_start"].isna() & df.get("DateTime_end").notna()
    df.loc[mask, "DateTime_start"] = pd.to_datetime(
        df.loc[mask, "DateTime_end"], errors="coerce"
    )

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

    for col in ["Category", "City", "EventName", "Description"]:
        df[col] = df[col].fillna("").astype(str)

    return df


# -------------------------------------------------
# FILTRES
# -------------------------------------------------
def filter_by_category(df, interests_param):
    if df.empty or not interests_param or "Category" not in df.columns:
        return df

    interests = {}
    for part in interests_param.split(","):
        if ":" in part:
            name, weight = part.split(":", 1)
            try:
                interests[normalize_text(name)] = int(weight)
            except ValueError:
                continue

    if not interests:
        return df

    def score(cell):
        cell_norm = normalize_text(cell)
        return sum(
            weight
            for name, weight in interests.items()
            if name in cell_norm
        )

    df = df.copy()
    df["interest_score"] = df["Category"].apply(score)

    return df[df["interest_score"] > 0]


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
