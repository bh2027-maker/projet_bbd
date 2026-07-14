# data/fetch_data.py
import requests
import pandas as pd
import os

# Codes INSEE ou liste des communes du Massif des Bauges (< 2500 hab)
COMMUNES_BAUGES = [
    {"nom": "Bellecombe-en-Bauges", "code_insee": "73039", "code_postal": "73340"},
    {"nom": "Doucy-en-Bauges", "code_insee": "73101", "code_postal": "73630"},
    {"nom": "La Motte-en-Bauges", "code_insee": "73179", "code_postal": "73340"},
    {"nom": "Lescheraines", "code_insee": "73146", "code_postal": "73340"},
    {"nom": "Le Châtelard", "code_insee": "73081", "code_postal": "73630"},
    {"nom": "Aillon-le-Jeune", "code_insee": "73004", "code_postal": "73340"},
    {"nom": "Aillon-le-Vieux", "code_insee": "73005", "code_postal": "73340"},
    {"nom": "Jarsy", "code_insee": "73138", "code_postal": "73630"},
    {"nom": "Arith", "code_insee": "73020", "code_postal": "73340"},
    {"nom": "Ecole", "code_insee": "73106", "code_postal": "73630"}
]

def fetch_communes_metadata():
    """Récupère les informations démographiques via GeoAPI (INSEE)"""
    print("⏳ Récupération des données communes INSEE...")
    list_communes = []
    
    for c in COMMUNES_BAUGES:
        url = f"https://geo.api.gouv.fr/communes/{c['code_insee']}?fields=nom,code,population,codesPostaux"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            list_communes.append({
                "code_insee": c['code_insee'],
                "nom_commune": data.get("nom"),
                "population": data.get("population"),
                "code_postal": c['code_postal'],
                "zone_climatique": "H1", # Le Massif des Bauges est à 100% en zone H1
                "altitude_moyenne": 850 # Estimation de moyenne montagne
            })
            
    df = pd.DataFrame(list_communes)
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv("data/raw/bauges_communes.csv", index=False)
    print(f"✅ {len(df)} communes sauvegardées dans data/raw/bauges_communes.csv")
    return df

def fetch_maisons_ban(code_insee, nom_commune):
    """Récupère toutes les adresses d'une commune via l'API Base Adresse Nationale"""
    print(f"⏳ Extraction des adresses BAN pour {nom_commune}...")
    url = f"https://api-adresse.data.gouv.fr/search/?q={nom_commune}&citycode={code_insee}&limit=1000"
    res = requests.get(url)
    
    maisons = []
    if res.status_code == 200:
        features = res.json().get("features", [])
        for f in features:
            props = f.get("properties", {})
            geom = f.get("geometry", {})
            
            # Filtre pour exclure les noms de rues seules et garder les adresses précises
            if props.get("type") == "housenumber":
                coords = geom.get("coordinates", [0, 0])
                maisons.append({
                    "id_ban": props.get("id"),
                    "adresse": props.get("label"),
                    "nom_commune": nom_commune,
                    "code_post": props.get("postcode"),
                    "lon": coords[0],
                    "lat": coords[1],
                    # Valeurs par défaut enrichies ensuite par l'ADEME/Score
                    "type_batiment": "Maison Individuelle",
                    "annee_construction": 1988,  # Estimation moyenne
                    "surface_m2": 110,           # Estimation moyenne
                    "type_chauffage_probable": "fioul" # Hypothèse haute Bauges
                })
                
    return maisons

def run_pipeline():
    # 1. Mise à jour des communes
    fetch_communes_metadata()
    
    # 2. Récupération des maisons pour toutes les communes
    all_maisons = []
    for c in COMMUNES_BAUGES:
        maisons = fetch_maisons_ban(c["code_insee"], c["nom"])
        all_maisons.extend(maisons)
        
    df_maisons = pd.DataFrame(all_maisons)
    df_maisons.to_csv("data/raw/maisons_raw.csv", index=False)
    print(f"🚀 Total : {len(df_maisons)} adresses de maisons extraites !")

if __name__ == "__main__":
    run_pipeline()
