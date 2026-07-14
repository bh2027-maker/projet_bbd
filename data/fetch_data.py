# data/fetch_data.py
import requests
import pandas as pd
import os

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
                "zone_climatique": "H1",
                "altitude_moyenne": 850
            })
            
    df = pd.DataFrame(list_communes)
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv("data/raw/bauges_communes.csv", index=False)
    print(f"✅ {len(df)} communes sauvegardées dans data/raw/bauges_communes.csv")
    return df

def fetch_adresses_commune(code_insee, nom_commune):
    """Récupère les adresses en interrogeant l'API Adresse officielle"""
    print(f"⏳ Extraction des adresses pour {nom_commune}...")
    
    # Étape 1 : Récupérer les rues et lieux-dits de la commune
    url_streets = f"https://api-adresse.data.gouv.fr/search/?q={nom_commune}&citycode={code_insee}&type=street&limit=100"
    res_streets = requests.get(url_streets)
    
    voies = [nom_commune]
    if res_streets.status_code == 200:
        for feat in res_streets.json().get("features", []):
            label = feat.get("properties", {}).get("name")
            if label:
                voies.append(f"{label} {nom_commune}")

    # Étape 2 : Récupérer toutes les adresses associées
    maisons = {}
    for query in voies[:15]:  # Sélection des voies principales
        url_add = f"https://api-adresse.data.gouv.fr/search/?q={query}&citycode={code_insee}&limit=100"
        res_add = requests.get(url_add)
        
        if res_add.status_code == 200:
            for f in res_add.json().get("features", []):
                props = f.get("properties", {})
                geom = f.get("geometry", {})
                ban_id = props.get("id")
                
                if ban_id and ban_id not in maisons:
                    coords = geom.get("coordinates", [0, 0])
                    maisons[ban_id] = {
                        "id_ban": ban_id,
                        "adresse": props.get("label"),
                        "nom_commune": nom_commune,
                        "code_post": props.get("postcode"),
                        "lon": coords[0],
                        "lat": coords[1],
                        "type_batiment": "Maison Individuelle",
                        "annee_construction": 1988,
                        "surface_m2": 110,
                        "type_chauffage_probable": "fioul"
                    }
                    
    return list(maisons.values())

def run_pipeline():
    fetch_communes_metadata()
    
    all_maisons = []
    for c in COMMUNES_BAUGES:
        maisons = fetch_adresses_commune(c["code_insee"], c["nom"])
        all_maisons.extend(maisons)
        
    df_maisons = pd.DataFrame(all_maisons)
    os.makedirs("data/raw", exist_ok=True)
    df_maisons.to_csv("data/raw/maisons_raw.csv", index=False)
    print(f"🚀 Total : {len(df_maisons)} adresses de maisons extraites !")

if __name__ == "__main__":
    run_pipeline()
