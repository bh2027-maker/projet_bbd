# data/fetch_data.py
import requests
import pandas as pd
import os
import io

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

def fetch_adresses_commune_bal(code_insee, nom_commune):
    """Télécharge l'intégralité du fichier d'adresses BAL pour une commune"""
    print(f"⏳ Extraction des adresses complètes pour {nom_commune}...")
    
    # URL de téléchargement direct de la Base Adresse Locale de la commune
    url = f"https://ban-ingestion.api.gouv.fr/communes/{code_insee}/download/csv-bal"
    res = requests.get(url)
    
    maisons = []
    if res.status_code == 200:
        # Lire le CSV retourné par l'API
        csv_data = io.StringIO(res.text)
        df_bal = pd.read_csv(csv_data, sep=';', dtype=str)
        
        for _, row in df_bal.iterrows():
            numero = str(row.get('numero', '')).strip()
            nom_voie = str(row.get('nom_voie', '')).strip()
            
            # Formater l'adresse complète
            adresse_complete = f"{numero} {nom_voie}".strip() if numero and numero != 'nan' else nom_voie
            
            lat = row.get('lat')
            lon = row.get('long') or row.get('lon')
            
            if lat and lon:
                maisons.append({
                    "id_ban": row.get('cle_interop'),
                    "adresse": f"{adresse_complete}, {nom_commune}",
                    "nom_commune": nom_commune,
                    "code_post": row.get('code_postal'),
                    "lon": float(lon),
                    "lat": float(lat),
                    "type_batiment": "Maison Individuelle",
                    "annee_construction": 1988,  # Valeur par défaut pour le scoring
                    "surface_m2": 110,           # Valeur par défaut pour le scoring
                    "type_chauffage_probable": "fioul"
                })
    else:
        # Fallback si pas de BAL directe : requête générique adresse.data.gouv.fr
        fallback_url = f"https://api-adresse.data.gouv.fr/search/?q={nom_commune}&limit=100"
        res_fb = requests.get(fallback_url)
        if res_fb.status_code == 200:
            for f in res_fb.json().get("features", []):
                props = f.get("properties", {})
                geom = f.get("geometry", {})
                coords = geom.get("coordinates", [0, 0])
                maisons.append({
                    "id_ban": props.get("id"),
                    "adresse": props.get("label"),
                    "nom_commune": nom_commune,
                    "code_post": props.get("postcode"),
                    "lon": coords[0],
                    "lat": coords[1],
                    "type_batiment": "Maison Individuelle",
                    "annee_construction": 1988,
                    "surface_m2": 110,
                    "type_chauffage_probable": "fioul"
                })
                
    return maisons

def run_pipeline():
    fetch_communes_metadata()
    
    all_maisons = []
    for c in COMMUNES_BAUGES:
        maisons = fetch_adresses_commune_bal(c["code_insee"], c["nom"])
        all_maisons.extend(maisons)
        
    df_maisons = pd.DataFrame(all_maisons)
    os.makedirs("data/raw", exist_ok=True)
    df_maisons.to_csv("data/raw/maisons_raw.csv", index=False)
    print(f"🚀 Total : {len(df_maisons)} adresses de maisons extraites !")

if __name__ == "__main__":
    run_pipeline()
