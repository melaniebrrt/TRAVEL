import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

CSV_PATH = "data/events_monthly.csv"
OUTPUT_PATH = "data/event_embeddings.npy"

# Charger CSV du scrape mensuel
df = pd.read_csv(CSV_PATH)

# Texte à encoder
texts = (df['EventName'].fillna('') + ' ' + df['Description'].fillna('')).tolist()

# Charger le modèle
model = SentenceTransformer('all-MiniLM-L6-v2')

# Générer embeddings
print(f"Génération des embeddings pour {len(texts)} événements...")
embeddings = model.encode(texts, show_progress_bar=True, convert_to_tensor=False)

# Sauvegarder embeddings
np.save(OUTPUT_PATH, embeddings)
print(f"Embeddings sauvegardés dans {OUTPUT_PATH}")
